import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import networkx as nx
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import AgglomerativeClustering
import logging
from tqdm import tqdm
from collections import defaultdict

logger = logging.getLogger(__name__)


class GraphConvolutionalLayer(nn.Module):
    """Single GCN layer implementation."""
    
    def __init__(self, input_dim, output_dim, activation=True, dropout=0.1):
        super(GraphConvolutionalLayer, self).__init__()
        self.input_dim = input_dim
        self.output_dim = output_dim
        self.activation = activation
        
        # Linear transformation
        self.linear = nn.Linear(input_dim, output_dim)
        self.dropout = nn.Dropout(dropout)
        
    def forward(self, x, adj):
        """
        Forward pass for GCN layer.
        
        Args:
            x: Node features (N x input_dim)
            adj: Normalized adjacency matrix (N x N)
        
        Returns:
            Node embeddings (N x output_dim)
        """
        # Linear transformation
        h = self.linear(x)
        
        # Graph convolution: A * H * W
        h = torch.mm(adj, h)
        
        if self.activation:
            h = F.relu(h)
            
        h = self.dropout(h)
        
        return h


class AttentionGCN(nn.Module):
    """Graph Convolutional Network with attention mechanism for author disambiguation."""
    
    def __init__(self, input_dim, hidden_dims=[128, 64], num_layers=3, dropout=0.1):
        super(AttentionGCN, self).__init__()
        self.num_layers = num_layers
        self.layers = nn.ModuleList()
        
        # Build GCN layers
        dims = [input_dim] + hidden_dims
        for i in range(len(dims) - 1):
            self.layers.append(GraphConvolutionalLayer(
                dims[i], dims[i+1], activation=(i < len(dims) - 2), dropout=dropout
            ))
        
        # Attention mechanism - create separate attention layers for each GCN layer output
        self.attention_layers = nn.ModuleList()
        for dim in dims[1:]:  # Skip input_dim, start from first hidden layer
            self.attention_layers.append(nn.Linear(dim, 1))
        
    def forward(self, x, adj):
        """
        Forward pass with attention mechanism.
        
        Args:
            x: Node features
            adj: Normalized adjacency matrix
            
        Returns:
            Final node embeddings with attention
        """
        layer_outputs = []
        h = x
        
        # Pass through all layers and collect outputs
        for layer in self.layers:
            h = layer(h, adj)
            layer_outputs.append(h)
        
        # Apply attention mechanism
        if len(layer_outputs) > 1:
            # Use the last layer's output as the target dimension
            target_dim = layer_outputs[-1].shape[1]
            target_shape = layer_outputs[-1].shape
            
            # Calculate attention weights for each layer output
            attention_weights = []
            for i, output in enumerate(layer_outputs):
                # Use global mean pooling over nodes for attention calculation
                pooled = torch.mean(output, dim=0)  # Shape: [hidden_dim]
                
                weight = torch.sigmoid(self.attention_layers[i](pooled.unsqueeze(0)))  # Shape: [1, 1]
                attention_weights.append(weight.squeeze())  # Shape: [1]
            
            # Normalize attention weights
            attention_weights = torch.stack(attention_weights, dim=0)  # Shape: [num_layers]
            attention_weights = F.softmax(attention_weights, dim=0)
            
            # Weighted combination of layer outputs (project to final layer dimensions)
            final_output = torch.zeros(target_shape, device=layer_outputs[0].device)
            for i, output in enumerate(layer_outputs):
                if output.shape[1] != target_dim:
                    # Project to target dimension using linear interpolation (simple approach)
                    # For a more sophisticated approach, we could use learned projections
                    if output.shape[1] > target_dim:
                        # Downsample by taking first target_dim features
                        projected_output = output[:, :target_dim]
                    else:
                        # Upsample by padding with zeros
                        padding = target_dim - output.shape[1]
                        projected_output = F.pad(output, (0, padding), 'constant', 0)
                else:
                    projected_output = output
                
                final_output += attention_weights[i] * projected_output
            
            return final_output
        else:
            return layer_outputs[0]


class GCNAuthorMatcher:
    """GCN-based author disambiguation system."""
    
    def __init__(self, 
                 embedding_dim=300,
                 hidden_dims=[128, 64],
                 learning_rate=0.01,
                 margin=1.0,
                 device='cpu'):
        
        self.embedding_dim = embedding_dim
        self.hidden_dims = hidden_dims
        self.learning_rate = learning_rate
        self.margin = margin
        self.device = torch.device(device)
        
        # Initialize vectorizers
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=1000,
            stop_words='english',
            ngram_range=(1, 2)
        )
        
        # Will be initialized during training
        self.paper_gcn = None
        self.author_gcn = None
        
        logger.info("🧠 GCN Author Matcher initialized")
        
    def preprocess_data(self, author_file_path, papers_file_path):
        """
        Preprocess both author and paper data.
        
        Args:
            author_file_path: Path to the JSON file containing author data
            papers_file_path: Path to the JSON file containing paper data
            
        Returns:
            A tuple of (papers_data, authors_features, author_work_map)
        """
        import json
        
        logger.info("📚 Loading data from JSON files...")
        
        # Load authors data
        try:
            with open(author_file_path, 'r', encoding='utf-8') as f:
                authors_data = json.load(f)
            logger.info(f"✅ Loaded {len(authors_data)} authors from {author_file_path}")
        except Exception as e:
            logger.error(f"⚠️ Failed to load authors file: {e}")
            authors_data = {}
        
        # Load papers data
        try:
            with open(papers_file_path, 'r', encoding='utf-8') as f:
                papers_raw = json.load(f)
                
                # Convert list to dictionary with IDs if necessary
                if isinstance(papers_raw, list):
                    papers_data = {}
                    for paper in papers_raw:
                        paper_id = paper.get('id', '') or paper.get('paper_id', '') or f"paper_{len(papers_data)}"
                        papers_data[paper_id] = paper
                else:
                    papers_data = papers_raw
                    
            logger.info(f"✅ Loaded {len(papers_data)} papers from {papers_file_path}")
        except Exception as e:
            logger.error(f"⚠️ Failed to load papers file: {e}")
            papers_data = {}
            
        # Create author features dictionary with normalized IDs
        authors_features = {}
        normalized_id_map = {}
        
        for author_id, author_data in authors_data.items():
            # Normalize author ID format 
            # Store both the full URL format and the short ID format
            if author_id.startswith('https://'):
                short_id = author_id.split('/')[-1]
            else:
                short_id = author_id
                if not author_id.startswith('A'):
                    author_id = f"https://openalex.org/{author_id}"
            
            normalized_id_map[author_id] = short_id
            normalized_id_map[short_id] = short_id
            
            # Extract relevant features for each author
            features = {
                'name': author_data.get('display_name', ''),
                'orcid': author_data.get('orcid', ''),
                'institution': self._extract_institution_name(author_data),
                'concepts': self._extract_concepts(author_data),
                'paper_count': len(author_data.get('works', [])),
                'citations': author_data.get('cited_by_count', 0)
            }
            
            # Store features for both ID formats to maximize matching chance
            authors_features[short_id] = features
            if short_id != author_id:
                authors_features[author_id] = features
            
        # Create author to work mapping with normalized IDs
        author_work_map = {}
        for author_id, author_data in authors_data.items():
            short_id = normalized_id_map.get(author_id, author_id)
            author_work_map[short_id] = set(author_data.get('works', []))
            
        logger.info(f"🔄 Normalized {len(normalized_id_map)} author IDs for consistent matching")
            
        # Ensure papers have the right format and author connections
        enhanced_papers = {}
        for paper_id, paper_data in papers_data.items():
            # Make sure each paper has an authors list with proper format
            enhanced_paper = dict(paper_data)
            
            # Process the authors list to ensure it's in the expected format with IDs
            authors_list = []
            for author in paper_data.get('authorships', []):
                if isinstance(author, dict):
                    # Check for the OpenAlex format where author is under 'author' key
                    if 'author' in author and isinstance(author['author'], dict):
                        author_id = author['author'].get('id', '')
                        # Keep the full ID format but note it for consistency checking
                        author_info = {
                            'id': author_id,
                            'name': author['author'].get('display_name', ''),
                            'orcid': author['author'].get('orcid', '')
                        }
                        authors_list.append(author_info)
                    # Check for direct id in the author dict
                    elif 'id' in author:
                        authors_list.append(author)
                    # If no ID but has a name, create a synthetic ID
                    elif 'name' in author and author['name']:
                        author_info = {
                            'id': f"synthetic_{hash(author['name']) % 10000000}",
                            'name': author['name'],
                            'orcid': author.get('orcid', '')
                        }
                        authors_list.append(author_info)
            
            # Update the paper with proper authors list
            enhanced_paper['authors'] = authors_list
            enhanced_papers[paper_id] = enhanced_paper
            
        logger.info(f"🔄 Processed {len(enhanced_papers)} papers with author connections")
        return enhanced_papers, authors_features, author_work_map
        
    def _extract_institution_name(self, author_data):
        """Extract the main institution name from author data."""
        if 'last_known_institution' in author_data and author_data['last_known_institution']:
            if isinstance(author_data['last_known_institution'], dict):
                return author_data['last_known_institution'].get('display_name', '')
        return ''
    
    def _extract_concepts(self, author_data):
        """Extract concepts from author data."""
        concepts = []
        if 'x_concepts' in author_data and isinstance(author_data['x_concepts'], list):
            for concept in author_data['x_concepts']:
                if isinstance(concept, dict) and 'display_name' in concept:
                    concepts.append(concept['display_name'])
        return concepts

    def extract_paper_features(self, papers_data, author_work_map):
        """Extract features for papers using TF-IDF."""
        logger.info("📝 Extracting paper features...")
        
        # Collect all text content for TF-IDF
        paper_texts = []
        paper_ids = []
        
        for paper_id, paper_data in papers_data.items():
            # Combine title, abstract, keywords, venue
            text_parts = []
            
            if paper_data.get('title'):
                text_parts.append(str(paper_data['title']))
            if paper_data.get('abstract'):
                text_parts.append(str(paper_data['abstract']))
            if paper_data.get('keywords'):
                if isinstance(paper_data['keywords'], list):
                    text_parts.extend([str(k) for k in paper_data['keywords']])
                else:
                    text_parts.append(str(paper_data['keywords']))
            if paper_data.get('venue'):
                text_parts.append(str(paper_data['venue']))
            
            # Add author names
            for author in paper_data.get('authors', []):
                if isinstance(author, dict) and author.get('name'):
                    text_parts.append(str(author['name']))
                elif isinstance(author, str):
                    text_parts.append(str(author))
            
            paper_text = ' '.join(text_parts)
            
            # Only add non-empty texts
            if paper_text.strip():
                paper_texts.append(paper_text)
                paper_ids.append(paper_id)
        
        # Check if we have any papers
        if not paper_texts:
            logger.warning("⚠️ No paper texts found for feature extraction")
            return {}, []
        
        # Add some dummy text if all texts are empty or just stop words
        if len(paper_texts) < 3:
            logger.info("🔧 Adding dummy documents to prevent vocabulary issues")
            paper_texts.extend([
                "machine learning artificial intelligence",
                "data science computer vision",
                "natural language processing"
            ])
            paper_ids.extend(["dummy_1", "dummy_2", "dummy_3"])
        
        try:
            # Fit TF-IDF vectorizer
            tfidf_matrix = self.tfidf_vectorizer.fit_transform(paper_texts)
            
            # Convert to dense numpy array
            features = tfidf_matrix.toarray()
            
            # Remove dummy entries if we added them
            real_papers = len(papers_data)
            if len(paper_ids) > real_papers:
                features = features[:real_papers]
                paper_ids = paper_ids[:real_papers]
            
            return dict(zip(paper_ids, features)), paper_ids
            
        except ValueError as e:
            if "empty vocabulary" in str(e):
                logger.warning("⚠️ Empty vocabulary detected, creating minimal features")
                # Create minimal feature vectors
                features = np.random.rand(len(paper_ids), 100)  # 100-dim random features
                return dict(zip(paper_ids, features)), paper_ids
            else:
                raise e

    def build_paper_paper_graph(self, paper_features, threshold=0.3):
        """Build paper-to-paper graph based on feature similarity."""
        logger.info("🔗 Building paper-to-paper graph...")
        
        paper_ids = list(paper_features.keys())
        n_papers = len(paper_ids)
        
        logger.info(f"   Processing {n_papers} papers for similarity computation...")
        
        # Create adjacency matrix
        adj_matrix = np.zeros((n_papers, n_papers))
        
        # Use tqdm to show progress
        connections_found = 0
        total_comparisons = n_papers * (n_papers - 1) // 2
        similarities = []  # Track all similarities for analysis
        
        with tqdm(total=total_comparisons, desc="Paper similarity", unit="pairs") as pbar:
            for i, paper_i in enumerate(paper_ids):
                for j, paper_j in enumerate(paper_ids[i+1:], i+1):
                    # Calculate cosine similarity
                    feat_i = paper_features[paper_i]
                    feat_j = paper_features[paper_j]
                    
                    similarity = np.dot(feat_i, feat_j) / (
                        np.linalg.norm(feat_i) * np.linalg.norm(feat_j) + 1e-8
                    )
                    
                    similarities.append(similarity)
                    
                    if similarity > threshold:
                        adj_matrix[i, j] = similarity
                        adj_matrix[j, i] = similarity
                        connections_found += 1
                    
                    pbar.update(1)
                    
                    # Update description periodically
                    if pbar.n % 1000 == 0:
                        pbar.set_description(f"Paper similarity (found {connections_found} connections)")
        
        # Log similarity statistics
        if similarities:
            max_sim = max(similarities)
            min_sim = min(similarities)
            avg_sim = sum(similarities) / len(similarities)
            logger.info(f"   📊 Similarity stats: min={min_sim:.3f}, max={max_sim:.3f}, avg={avg_sim:.3f}")
            
            # If no connections found, try with lower threshold
            if connections_found == 0 and n_papers > 1:
                logger.warning(f"⚠️ No connections found with threshold {threshold}, trying adaptive threshold...")
                # Use a percentile-based threshold instead
                sorted_sims = sorted(similarities, reverse=True)
                # Take top 10% of similarities or at least some connections
                adaptive_threshold = sorted_sims[min(len(sorted_sims)//10, len(sorted_sims)-1)]
                adaptive_threshold = max(adaptive_threshold, 0.1)  # Minimum threshold
                
                logger.info(f"   🔧 Using adaptive threshold: {adaptive_threshold:.3f}")
                
                # Rebuild with adaptive threshold
                adj_matrix = np.zeros((n_papers, n_papers))
                connections_found = 0
                
                for i, paper_i in enumerate(paper_ids):
                    for j, paper_j in enumerate(paper_ids[i+1:], i+1):
                        feat_i = paper_features[paper_i]
                        feat_j = paper_features[paper_j]
                        
                        similarity = np.dot(feat_i, feat_j) / (
                            np.linalg.norm(feat_i) * np.linalg.norm(feat_j) + 1e-8
                        )
                        
                        if similarity > adaptive_threshold:
                            adj_matrix[i, j] = similarity
                            adj_matrix[j, i] = similarity
                            connections_found += 1
        
        logger.info(f"   ✅ Found {connections_found} paper-paper connections")
        return adj_matrix, paper_ids

    def build_coauthor_graph(self, papers_data, author_work_map):
        """Build coauthor graph."""
        logger.info("👥 Building coauthor graph...")
        
        # Count coauthor relationships
        coauthor_counts = defaultdict(int)
        all_authors = set()
        papers_processed = 0
        
        # Use tqdm for papers processing
        for paper_id, paper_data in tqdm(papers_data.items(), desc="Processing papers for coauthors"):
            authors = []
            for author in paper_data.get('authors', []):
                if isinstance(author, dict):
                    author_id = author.get('id', '')
                    if author_id:
                        authors.append(author_id)
            
            all_authors.update(authors)
            papers_processed += 1
            
            # Count pairwise collaborations
            for i, author_i in enumerate(authors):
                for author_j in authors[i+1:]:
                    pair = tuple(sorted([author_i, author_j]))
                    coauthor_counts[pair] += 1
        
        author_ids = list(all_authors)
        n_authors = len(author_ids)
        author_to_idx = {author_id: i for i, author_id in enumerate(author_ids)}
        
        logger.info(f"   📊 Stats: {papers_processed} papers, {n_authors} authors, {len(coauthor_counts)} coauthor pairs")
        
        # Create adjacency matrix
        adj_matrix = np.zeros((n_authors, n_authors))
        connections_added = 0
        
        # Use tqdm for building adjacency matrix
        for (author_i, author_j), count in tqdm(coauthor_counts.items(), desc="Building coauthor adjacency matrix"):
            if author_i in author_to_idx and author_j in author_to_idx:
                i = author_to_idx[author_i]
                j = author_to_idx[author_j]
                # Normalize by log to prevent dominance of highly collaborative pairs
                weight = np.log(count + 1) / 10.0
                adj_matrix[i, j] = weight
                adj_matrix[j, i] = weight
                connections_added += 1
        
        logger.info(f"   ✅ Added {connections_added} coauthor connections to adjacency matrix")
        
        # If no coauthor connections found, create some artificial connections based on shared research areas
        if connections_added == 0 and n_authors > 1:
            logger.warning("⚠️ No coauthor connections found, creating similarity-based connections...")
            
            # Extract author research topics/concepts for similarity
            author_concepts = {}
            for author_id in author_ids:
                concepts = set()
                # Get papers by this author and extract concepts
                for paper_id, paper_data in papers_data.items():
                    for author in paper_data.get('authors', []):
                        if isinstance(author, dict):
                            # Check if this is the current author
                            if author.get('id', '') == author_id:
                                # Add paper concepts
                                for concept in paper_data.get('concepts', []):
                                    if isinstance(concept, dict):
                                        concepts.add(concept.get('display_name', '').lower())
                author_concepts[author_id] = concepts
            
            # Create connections based on shared concepts
            concept_connections = 0
            for i, author_i in enumerate(author_ids):
                for j, author_j in enumerate(author_ids[i+1:], i+1):
                    concepts_i = author_concepts.get(author_i, set())
                    concepts_j = author_concepts.get(author_j, set())
                    
                    if concepts_i and concepts_j:
                        shared = len(concepts_i.intersection(concepts_j))
                        total = len(concepts_i.union(concepts_j))
                        
                        if total > 0:
                            similarity = shared / total
                            if similarity > 0.1:  # Low threshold for concept similarity
                                adj_matrix[i, j] = similarity * 0.5  # Lower weight than coauthorship
                                adj_matrix[j, i] = similarity * 0.5
                                concept_connections += 1
            
            logger.info(f"   🔧 Added {concept_connections} concept-based connections")
        
        return adj_matrix, author_ids

    def build_paper_author_graph(self, papers_data, paper_ids, author_ids):
        """Build paper-to-author bipartite graph."""
        logger.info("📄👤 Building paper-author graph...")
        
        paper_to_idx = {paper_id: i for i, paper_id in enumerate(paper_ids)}
        author_to_idx = {author_id: i for i, author_id in enumerate(author_ids)}
        
        n_papers = len(paper_ids)
        n_authors = len(author_ids)
        
        # Create bipartite adjacency matrix
        adj_matrix = np.zeros((n_papers, n_authors))
        
        relationships_added = 0
        
        for paper_id, paper_data in tqdm(papers_data.items(), desc="Building paper-author relationships"):
            if paper_id not in paper_to_idx:
                continue
                
            paper_idx = paper_to_idx[paper_id]
            
            for author in paper_data.get('authors', []):
                if isinstance(author, dict):
                    author_id = author.get('id', '')
                    if author_id and author_id in author_to_idx:
                        author_idx = author_to_idx[author_id]
                        adj_matrix[paper_idx, author_idx] = 1.0
                        relationships_added += 1
        
        logger.info(f"   Added {relationships_added} paper-author relationships")
        return adj_matrix

    def normalize_adjacency_matrix(self, adj_matrix):
        """Normalize adjacency matrix for GCN."""
        # Add self-connections
        adj_matrix = adj_matrix + np.eye(adj_matrix.shape[0])
        
        # Calculate degree matrix
        degree_matrix = np.diag(np.sum(adj_matrix, axis=1))
        
        # D^(-1/2) * A * D^(-1/2)
        degree_inv_sqrt = np.diag(1.0 / np.sqrt(np.diag(degree_matrix) + 1e-8))
        normalized_adj = degree_inv_sqrt @ adj_matrix @ degree_inv_sqrt
        
        return normalized_adj

    def triplet_loss(self, anchor, positive, negative, margin=1.0):
        """Calculate triplet loss."""
        pos_dist = F.pairwise_distance(anchor, positive)
        neg_dist = F.pairwise_distance(anchor, negative)
        
        loss = F.relu(pos_dist - neg_dist + margin)
        return loss.mean()

    def generate_triplets(self, embeddings, adj_matrix, num_triplets=1000):
        """Generate triplets for training."""
        triplets = []
        n_nodes = embeddings.shape[0]
        
        # Check if adjacency matrix has any connections at all
        total_connections = np.sum(adj_matrix > 0)
        if total_connections == 0:
            logger.warning("⚠️ Adjacency matrix has no connections, creating minimal synthetic triplets")
            
            # Create some synthetic triplets based on random sampling
            # This allows training to proceed even without real connections
            if n_nodes >= 3:
                synthetic_triplets = min(100, num_triplets)  # Limit synthetic triplets
                for _ in range(synthetic_triplets):
                    # Random sampling for synthetic triplets
                    indices = np.random.choice(n_nodes, size=3, replace=False)
                    triplets.append((indices[0], indices[1], indices[2]))
                
                logger.info(f"🔧 Generated {len(triplets)} synthetic triplets for minimal training")
            
            return triplets
        
        # Find all nodes that have at least one connection
        nodes_with_connections = np.where(np.sum(adj_matrix, axis=1) > 0)[0]
        if len(nodes_with_connections) == 0:
            logger.warning("⚠️ No nodes with connections found")
            return triplets
        
        logger.info(f"📊 Adjacency matrix stats: {total_connections} connections, {len(nodes_with_connections)}/{n_nodes} nodes connected")
        
        # Adaptive number of triplets based on available connections
        available_triplets = 0
        for node in nodes_with_connections:
            connected = np.sum(adj_matrix[node] > 0)
            not_connected = n_nodes - connected - 1  # -1 for self
            available_triplets += min(connected, not_connected)
        
        target_triplets = min(num_triplets, available_triplets, 1000)  # Cap at reasonable number
        logger.info(f"🎯 Targeting {target_triplets} triplets (requested: {num_triplets}, available: {available_triplets})")
        
        max_attempts = target_triplets * 20  # More generous attempt limit
        attempts = 0
        
        while len(triplets) < target_triplets and attempts < max_attempts:
            attempts += 1
            
            # Choose anchor from nodes that have connections
            if len(nodes_with_connections) == 0:
                break
                
            anchor_idx = np.random.choice(nodes_with_connections)
            
            # Find positive (connected) and negative (not connected) samples
            connected = np.where(adj_matrix[anchor_idx] > 0)[0]
            not_connected = np.where(adj_matrix[anchor_idx] == 0)[0]
            
            # Remove anchor from not_connected to avoid self-comparison
            not_connected = not_connected[not_connected != anchor_idx]
            
            if len(connected) > 0 and len(not_connected) > 0:
                positive_idx = np.random.choice(connected)
                negative_idx = np.random.choice(not_connected)
                
                triplets.append((anchor_idx, positive_idx, negative_idx))
        
        if len(triplets) == 0:
            logger.warning("⚠️ Could not generate any valid triplets for training")
        else:
            logger.info(f"✅ Generated {len(triplets)} triplets for training (attempts: {attempts})")
        
        return triplets

    def train_gcn(self, features, adj_matrix, num_epochs=100):
        """Train GCN model."""
        n_nodes, feature_dim = features.shape
        
        # Initialize GCN
        gcn = AttentionGCN(
            input_dim=feature_dim,
            hidden_dims=self.hidden_dims
        ).to(self.device)
        
        optimizer = torch.optim.Adam(gcn.parameters(), lr=self.learning_rate)
        
        # Convert to torch tensors
        features_tensor = torch.FloatTensor(features).to(self.device)
        adj_tensor = torch.FloatTensor(adj_matrix).to(self.device)
        
        logger.info(f"🔥 Training GCN for {num_epochs} epochs...")
        
        epochs_without_triplets = 0
        max_epochs_without_triplets = 10
        
        # Use tqdm for epoch progress
        with tqdm(range(num_epochs), desc="Training GCN", unit="epoch") as pbar:
            for epoch in pbar:
                gcn.train()
                optimizer.zero_grad()
                
                # Forward pass
                embeddings = gcn(features_tensor, adj_tensor)
                
                # Generate triplets
                triplets = self.generate_triplets(
                    embeddings.detach().cpu().numpy(), 
                    adj_matrix
                )
                
                if len(triplets) == 0:
                    epochs_without_triplets += 1
                    pbar.set_description(f"Training GCN (no triplets: {epochs_without_triplets}/{max_epochs_without_triplets})")
                    if epochs_without_triplets >= max_epochs_without_triplets:
                        logger.warning(f"⚠️ No triplets generated for {max_epochs_without_triplets} consecutive epochs, stopping training early")
                        break
                    continue
                
                epochs_without_triplets = 0  # Reset counter when we get triplets
                
                # Calculate triplet loss
                total_loss = 0
                for anchor_idx, pos_idx, neg_idx in triplets:
                    anchor = embeddings[anchor_idx:anchor_idx+1]
                    positive = embeddings[pos_idx:pos_idx+1]
                    negative = embeddings[neg_idx:neg_idx+1]
                    
                    loss = self.triplet_loss(anchor, positive, negative, self.margin)
                    total_loss += loss
                
                if len(triplets) > 0:
                    total_loss /= len(triplets)
                    total_loss.backward()
                    optimizer.step()
                
                # Update progress bar
                pbar.set_description(f"Training GCN (Loss: {total_loss.item():.4f}, Triplets: {len(triplets)})")
                
                if epoch % 20 == 0:
                    logger.info(f"Epoch {epoch}, Loss: {total_loss.item():.4f}, Triplets: {len(triplets)}")
        
        return gcn

    def find_candidates(self, authors_data_path=None, papers_data_path=None, authors_features=None, author_work_map=None, papers_data=None):
        """
        Find consolidation candidates using GCN approach.
        
        Args:
            authors_data_path: Path to the JSON file containing author data
            papers_data_path: Path to the JSON file containing paper data
            authors_features: Optional pre-loaded author features
            author_work_map: Optional pre-loaded author work map
            papers_data: Optional pre-loaded papers data
        """
        logger.info("🧠 Starting GCN-based author consolidation...")
        
        # Load and preprocess data if paths are provided
        if authors_data_path and papers_data_path:
            papers_data, authors_features, author_work_map = self.preprocess_data(
                authors_data_path, papers_data_path
            )
            
        if not authors_features or not papers_data:
            raise ValueError("Must provide either data paths or pre-loaded data")
        
        # Extract paper features
        paper_features, paper_ids = self.extract_paper_features(papers_data, author_work_map)
        
        # Build graphs
        paper_adj, _ = self.build_paper_paper_graph(paper_features)
        author_adj, author_ids = self.build_coauthor_graph(papers_data, author_work_map)
        paper_author_adj = self.build_paper_author_graph(papers_data, paper_ids, author_ids)
        
        # Normalize adjacency matrices
        paper_adj_norm = self.normalize_adjacency_matrix(paper_adj)
        author_adj_norm = self.normalize_adjacency_matrix(author_adj)
        
        # Prepare features
        paper_features_matrix = np.array([paper_features[pid] for pid in paper_ids])
        
        # Simple one-hot encoding for authors (since we have limited author features)
        author_features_matrix = np.eye(len(author_ids))
        
        # Train Paper-GCN
        logger.info("Training Paper-GCN...")
        self.paper_gcn = self.train_gcn(paper_features_matrix, paper_adj_norm)
        
        # Train Author-GCN
        logger.info("Training Author-GCN...")
        self.author_gcn = self.train_gcn(author_features_matrix, author_adj_norm)
        
        # Get final embeddings
        with torch.no_grad():
            paper_features_tensor = torch.FloatTensor(paper_features_matrix).to(self.device)
            paper_adj_tensor = torch.FloatTensor(paper_adj_norm).to(self.device)
            paper_embeddings = self.paper_gcn(paper_features_tensor, paper_adj_tensor)
            
            author_features_tensor = torch.FloatTensor(author_features_matrix).to(self.device)
            author_adj_tensor = torch.FloatTensor(author_adj_norm).to(self.device)
            author_embeddings = self.author_gcn(author_features_tensor, author_adj_tensor)
        
        # Cluster papers using hierarchical clustering
        logger.info("🔍 Clustering papers using hierarchical clustering...")
        paper_embeddings_np = paper_embeddings.cpu().numpy()
        
        # Use agglomerative clustering with optimized parameters
        # Lower distance threshold to create more granular clusters (helps with finding connections)
        clustering = AgglomerativeClustering(
            n_clusters=None,
            distance_threshold=1.0,  # Reduced from 1.5 to create more precise clusters
            linkage='average'  # Changed from 'ward' to 'average' for better cluster separation
        )
        
        paper_clusters = clustering.fit_predict(paper_embeddings_np)
        logger.info(f"   Found {len(set(paper_clusters))} paper clusters")
        
        # Build result graph
        G = nx.Graph()
        
        # Add author nodes
        logger.info("📝 Adding author nodes to graph...")
        for author_id in tqdm(authors_features.keys(), desc="Adding author nodes"):
            G.add_node(author_id, **authors_features[author_id])
        
        # Map paper clusters back to authors
        paper_to_cluster = dict(zip(paper_ids, paper_clusters))
        
        # Group authors by their paper clusters
        cluster_to_authors = defaultdict(set)
        author_to_clusters = defaultdict(set)
        
        # Track author ID normalization for debugging
        author_id_map = {}
        authors_missing = 0
        authors_matched = 0
        
        logger.info("🔗 Mapping paper clusters to authors...")
        for paper_id, cluster_id in tqdm(paper_to_cluster.items(), desc="Mapping clusters to authors"):
            paper_data = papers_data.get(paper_id, {})
            for author in paper_data.get('authors', []):
                if isinstance(author, dict):
                    # Handle different ID formats (full URL or just the ID part)
                    author_id_full = author.get('id', '')
                    author_id_short = author_id_full.split('/')[-1] if '/' in author_id_full else author_id_full
                    
                    # Try different ID formats to match with authors_features
                    found = False
                    for aid in [author_id_full, author_id_short, f"A{author_id_short}"]:
                        if aid and aid in authors_features:
                            cluster_to_authors[cluster_id].add(aid)
                            author_to_clusters[aid].add(cluster_id)
                            author_id_map[author_id_full] = aid
                            authors_matched += 1
                            found = True
                            break
                    
                    if not found:
                        authors_missing += 1
        
        # Create edges within clusters
        edges_added = 0
        logger.info("✨ Creating edges within clusters...")
        
        # Method 1: Connect authors within the same cluster
        for cluster_id, author_set in tqdm(cluster_to_authors.items(), desc="Creating direct cluster edges"):
            if len(author_set) <= 1:  # Skip clusters with only one author
                continue
                
            author_list = list(author_set)
            for i, author1 in enumerate(author_list):
                for author2 in author_list[i+1:]:
                    if not G.has_edge(author1, author2):
                        G.add_edge(author1, author2, 
                                 reason="gcn_direct_clustering", 
                                 confidence=0.85)
                        edges_added += 1
        
        # Method 2: Connect authors who share multiple clusters (stronger relationship)
        logger.info("🔍 Finding authors with shared cluster patterns...")
        authors_processed = set()
        
        for author_id, clusters in tqdm(author_to_clusters.items(), desc="Finding shared cluster patterns"):
            if len(clusters) < 1:  # Skip authors with no clusters (relaxed from < 2)
                continue
                
            authors_processed.add(author_id)
            
            # Find authors who share multiple clusters with this author
            for other_author, other_clusters in author_to_clusters.items():
                if other_author in authors_processed or other_author == author_id:
                    continue  # Skip already processed pairs and self-comparisons
                    
                shared_clusters = clusters.intersection(other_clusters)
                if len(shared_clusters) >= 1:  # Relaxed from >= 2 to >= 1 to find more connections
                    if not G.has_edge(author_id, other_author):
                        # Scale confidence based on number of shared clusters
                        confidence = min(0.9, 0.7 + 0.05 * len(shared_clusters))
                        G.add_edge(author_id, other_author,
                                 reason="gcn_shared_clusters",
                                 confidence=confidence)  # Higher confidence with more shared clusters
                        edges_added += 1
        
        # Method 3: Connect authors who've collaborated on papers
        logger.info("📚 Finding direct paper collaborations...")
        paper_author_pairs = defaultdict(set)
        
        # First build a mapping of papers to their authors
        for paper_id, paper_data in tqdm(papers_data.items(), desc="Mapping papers to authors"):
            for author in paper_data.get('authors', []):
                if isinstance(author, dict):
                    author_id = author.get('id', '')
                    # Try to find this author in authors_features using various ID formats
                    for aid in [author_id, author_id.split('/')[-1] if '/' in author_id else author_id]:
                        if aid in authors_features:
                            paper_author_pairs[paper_id].add(aid)
                            break
        
        # Now connect authors who collaborated on papers
        coauthor_edges = 0
        for paper_id, authors in tqdm(paper_author_pairs.items(), desc="Finding coauthors"):
            if len(authors) > 1:
                # Create edges between all coauthors
                authors_list = list(authors)
                for i, author1 in enumerate(authors_list):
                    for author2 in authors_list[i+1:]:
                        if not G.has_edge(author1, author2):
                            G.add_edge(author1, author2,
                                     reason="gcn_coauthorship",
                                     confidence=0.85)
                            edges_added += 1
                            coauthor_edges += 1
                            
        logger.info(f"   • Added {coauthor_edges} coauthor connections")
        
        # Calculate additional metrics for better insights
        clusters_with_multiple_authors = sum(1 for authors in cluster_to_authors.values() if len(authors) > 1)
        authors_with_multiple_clusters = sum(1 for clusters in author_to_clusters.values() if len(clusters) > 1)
        
        # Last resort: if no connections were found, use embedding similarity directly
        if edges_added == 0 and authors_features:
            logger.info("⚠️ No connections found through standard methods, attempting direct embedding similarity...")
            # Get author embeddings
            author_ids_list = list(authors_features.keys())
            
            if len(author_embeddings) >= len(author_ids_list):
                # Calculate pairwise cosine similarities between author embeddings
                author_embeddings_np = author_embeddings.cpu().numpy()
                from sklearn.metrics.pairwise import cosine_similarity
                
                # Limit to a manageable subset if too many authors
                max_authors = min(1000, len(author_ids_list))
                if len(author_ids_list) > max_authors:
                    logger.info(f"⚠️ Too many authors ({len(author_ids_list)}), limiting to {max_authors}")
                    author_ids_list = author_ids_list[:max_authors]
                    author_embeddings_np = author_embeddings_np[:max_authors]
                
                similarities = cosine_similarity(author_embeddings_np)
                
                # Add edges for highly similar authors
                similarity_threshold = 0.75
                fallback_edges = 0
                
                for i in range(len(author_ids_list)):
                    for j in range(i+1, len(author_ids_list)):
                        if similarities[i, j] > similarity_threshold:
                            author1 = author_ids_list[i]
                            author2 = author_ids_list[j]
                            if author1 in authors_features and author2 in authors_features:
                                if not G.has_edge(author1, author2):
                                    G.add_edge(author1, author2,
                                            reason="gcn_embedding_similarity",
                                            confidence=similarities[i, j])
                                    edges_added += 1
                                    fallback_edges += 1
                
                logger.info(f"   • Added {fallback_edges} edges based on embedding similarity")
        
        logger.info(f"✅ GCN consolidation completed: {edges_added} connections found")
        logger.info(f"   • Paper clusters: {len(set(paper_clusters))}")
        logger.info(f"   • Clusters with multiple authors: {clusters_with_multiple_authors}")
        logger.info(f"   • Authors in multiple clusters: {authors_with_multiple_clusters}")
        
        # Log mapping stats
        logger.info(f"   • Author mapping: {authors_matched} matches, {authors_missing} missing")
        logger.info(f"   • Author IDs mapped: {len(author_id_map)} unique author IDs")
            
        # If no edges were found, log a warning with potential reasons
        if edges_added == 0:
            logger.warning("⚠️ No author connections were established. Possible reasons:")
            logger.warning("   1. Not enough common papers between authors")
            logger.warning("   2. Paper clustering did not group related papers correctly")
            logger.warning("   3. Author data might be sparse or disconnected")
            logger.warning(f"   4. Author ID mismatches: {authors_missing} authors in papers not found in authors_features")
            
            # Check clustering metrics
            if len(set(paper_clusters)) < 3:
                logger.warning("   ⚠️ Very few paper clusters created. Check clustering parameters.")
                
            # Check if any clusters have multiple authors
            if clusters_with_multiple_authors == 0:
                logger.warning("   ⚠️ No clusters with multiple authors found. Check author-paper relationships.")
            
            # Check if authors were mapped to clusters
            if sum(len(authors) for authors in cluster_to_authors.values()) == 0:
                logger.warning("   ⚠️ No authors were mapped to paper clusters. Check author-paper relationships.")
        
        return G


def create_gcn_matcher(**kwargs):
    """Factory function to create GCN matcher."""
    return GCNAuthorMatcher(**kwargs)