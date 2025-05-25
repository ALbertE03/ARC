# GCN-Based Author Disambiguation

This directory contains the implementation of a Graph Convolutional Network (GCN) approach for author disambiguation, following research best practices in name disambiguation and scholarly data processing.

## Overview

The GCN approach implements a state-of-the-art deep learning solution for author consolidation that:

1. **Builds Multiple Graph Types**: Creates paper-to-paper, coauthor, and paper-to-author bipartite graphs
2. **Extracts Rich Features**: Uses TF-IDF vectorization of paper metadata (title, abstract, keywords, venue)
3. **Trains Attention-Based GCNs**: Employs Graph Convolutional Networks with attention mechanisms
4. **Uses Triplet Loss**: Optimizes embeddings using triplet loss for better separation
5. **Hierarchical Clustering**: Applies agglomerative clustering on learned embeddings

## Architecture

### Core Components

#### 1. GraphConvolutionalLayer

```python
class GraphConvolutionalLayer(nn.Module):
    """Single GCN layer with linear transformation and graph convolution."""
```

#### 2. AttentionGCN  

```python
class AttentionGCN(nn.Module):
    """Multi-layer GCN with attention mechanism for adaptive layer weighting."""
```

#### 3. GCNAuthorMatcher

```python
class GCNAuthorMatcher:
    """Complete GCN-based author disambiguation system."""
```

### Key Features

- **TF-IDF Feature Extraction**: Combines title, abstract, keywords, venue, and author names
- **Multiple Graph Construction**:
  - Paper-to-paper similarity graphs
  - Coauthor collaboration graphs  
  - Paper-to-author bipartite graphs
- **Attention Mechanism**: Adaptive weighting of different GCN layers
- **Triplet Loss Training**: Learns embeddings that separate different authors
- **Hierarchical Clustering**: Final consolidation using learned embeddings

## Usage

### Basic Usage

```python
from models.GCN import create_gcn_matcher

# Create GCN matcher
gcn_matcher = create_gcn_matcher(
    embedding_dim=300,
    hidden_dims=[128, 64],
    learning_rate=0.01,
    margin=1.0,
    device='cpu'  # or 'cuda' if available
)

# Find consolidation candidates
graph = gcn_matcher.find_candidates(
    authors_features, 
    author_work_map, 
    papers_data
)
```

### Using the Enhanced Consolidation Script

```bash
# Run GCN-based consolidation
python enhanced_consolidation.py --method gcn

# Run with limited authors for testing
python enhanced_consolidation.py --method gcn --max-authors 1000 --test-mode

# Run hybrid approach (traditional + GCN)
python enhanced_consolidation.py --method hybrid --save-to-db
```

### Comparing Approaches

```bash
# Compare traditional vs GCN approaches
python test_gcn_comparison.py
```

## Requirements

### Core Dependencies

- PyTorch >= 2.0.0
- NetworkX >= 2.8
- scikit-learn >= 1.0.0
- NumPy >= 1.21.0
- RapidFuzz >= 2.0.0

### Installation

```bash
# Install PyTorch (required for GCN)
pip install torch

# Install other dependencies
pip install -r requirements.txt
```

### Optional GPU Support

For faster training, install CUDA-enabled PyTorch:

```bash
# For CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

## Algorithm Details

### 1. Feature Extraction

The system extracts features from papers using TF-IDF vectorization:

```python
def extract_paper_features(self, papers_data, author_work_map):
    """Extract TF-IDF features from paper metadata."""
    # Combine title, abstract, keywords, venue, author names
    # Apply TF-IDF with n-grams (1,2) and max 1000 features
```

### 2. Graph Construction

#### Paper-to-Paper Graph

- Nodes: Papers
- Edges: Cosine similarity > threshold between TF-IDF vectors

#### Coauthor Graph  

- Nodes: Authors
- Edges: Weighted by log(collaboration_count + 1)

#### Paper-to-Author Graph

- Bipartite graph connecting papers to their authors

### 3. GCN Training

```python
def train_gcn(self, features, adj_matrix, num_epochs=100):
    """Train GCN using triplet loss."""
    # Initialize AttentionGCN
    # Generate triplets (anchor, positive, negative)
    # Optimize with triplet loss: max(0, d(a,p) - d(a,n) + margin)
```

### 4. Consolidation

Final consolidation uses hierarchical clustering on learned embeddings:

```python
clustering = AgglomerativeClustering(
    n_clusters=None,
    distance_threshold=1.5,
    linkage='ward'
)
```

## Performance Considerations

### Memory Usage

- TF-IDF matrices can be large for many papers
- Graph adjacency matrices scale as O(n²)
- Consider batching or sampling for very large datasets

### Training Time

- GCN training scales with graph size and number of epochs
- GPU acceleration recommended for large datasets
- Typical training: 50-100 epochs

### Accuracy vs Speed Trade-offs

- Higher embedding dimensions → better accuracy, slower training
- More GCN layers → better representation, more parameters
- Larger distance thresholds → fewer clusters, more consolidation

## Configuration Parameters

```python
gcn_matcher = GCNAuthorMatcher(
    embedding_dim=300,        # Final embedding dimension
    hidden_dims=[128, 64],    # GCN layer dimensions  
    learning_rate=0.01,       # Adam optimizer learning rate
    margin=1.0,               # Triplet loss margin
    device='cpu'              # 'cpu' or 'cuda'
)
```

### TF-IDF Parameters

```python
TfidfVectorizer(
    max_features=1000,        # Maximum vocabulary size
    stop_words='english',     # Remove English stop words
    ngram_range=(1, 2)        # Use unigrams and bigrams
)
```

### Clustering Parameters

```python
AgglomerativeClustering(
    n_clusters=None,          # Determine automatically
    distance_threshold=1.5,   # Cluster merging threshold
    linkage='ward'            # Linkage criterion
)
```

## Comparison with Traditional Approach

| Aspect | Traditional Rule-Based | GCN-Based |
|--------|----------------------|-----------|
| **Accuracy** | High precision, conservative | Good recall, data-driven |
| **Speed** | Fast for small datasets | Slower due to training |
| **Scalability** | O(n²) comparisons | Depends on graph sparsity |
| **Interpretability** | Clear rules | Black box |
| **Adaptability** | Manual rule tuning | Learns from data |
| **Dependencies** | Minimal | Requires PyTorch |

## Research Background

This implementation is based on recent advances in graph neural networks for name disambiguation:

1. **Graph Construction**: Multiple graph types capture different aspects of scholarly relationships
2. **Attention Mechanisms**: Allow the model to focus on most relevant information
3. **Triplet Loss**: Effective for learning discriminative embeddings
4. **Hierarchical Clustering**: Robust final step for grouping similar embeddings

## Troubleshooting

### Common Issues

#### 1. PyTorch Not Found

```bash
pip install torch
```

#### 2. CUDA Out of Memory

```python
# Reduce batch size or use CPU
device='cpu'
```

#### 3. No Edges Found

- Check data quality and graph construction parameters
- Verify TF-IDF feature extraction
- Adjust similarity thresholds

#### 4. Poor Performance

- Increase training epochs
- Adjust learning rate
- Try different embedding dimensions
- Check clustering parameters

### Debug Mode

Enable verbose logging:

```bash
python enhanced_consolidation.py --method gcn --verbose
```

### Performance Monitoring

The system logs:

- Training loss progression
- Graph construction statistics  
- Clustering results
- Execution times

## Future Improvements

1. **Dynamic Graph Updates**: Incremental updates for new papers/authors
2. **Multi-Modal Features**: Include citation patterns, temporal information
3. **Advanced Architectures**: Graph Attention Networks (GAT), GraphSAGE
4. **Active Learning**: Human-in-the-loop validation
5. **Federated Learning**: Privacy-preserving distributed training

## Contributing

When contributing to the GCN implementation:

1. **Test thoroughly** with both small and large datasets
2. **Document** all parameters and design decisions  
3. **Compare** against traditional approach
4. **Profile** memory usage and training time
5. **Validate** results manually for subset of data

## License

This implementation follows the same license as the main ARC project.
