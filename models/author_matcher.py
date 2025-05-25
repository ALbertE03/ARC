import networkx as nx
import logging
import itertools
from collections import defaultdict
from tqdm import tqdm
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer

logger = logging.getLogger(__name__)


class SmartAuthorMatcher:
    """Enhanced class to manage author consolidation using advanced ML techniques."""

    def __init__(self, similarity_threshold=0.90, batch_size=500):
        """Initialize the vectorizer and similarity parameters."""
        logger.info("🔍 Initializing robust author consolidation system...")
        self.similarity_threshold = similarity_threshold
        self.batch_size = batch_size

        self.char_vectorizer = TfidfVectorizer(
            analyzer="char_wb", ngram_range=(2, 4), min_df=1, max_df=1.0
        )

        self.word_vectorizer = TfidfVectorizer(
            analyzer="word", ngram_range=(1, 2), min_df=1, max_df=1.0
        )

        self.name_vectors = {}
        self.id_cache = {}

        self.eps = 0.15 
        self.min_samples = 1

        logger.info("✅ Robust consolidation system initialized correctly")

    def normalize_name_robust(self, name):
        """Normalize name with robust handling of hyphens and variations."""
        if not name:
            return ""
        normalized = name.lower().strip()
        
        normalized_no_hyphens = normalized.replace("-", " ")

        normalized_no_hyphens = " ".join(normalized_no_hyphens.split())
        
        return normalized_no_hyphens

    def are_names_equivalent(self, name1, name2):
        """Check if two names are equivalent considering hyphen variations."""
        if not name1 or not name2:
            return False
            
        norm1 = self.normalize_name_robust(name1)
        norm2 = self.normalize_name_robust(name2)
        
        # Exactamente iguales después de normalización
        if norm1 == norm2:
            return True
            
        # Verificar si uno es versión con guiones del otro
        # Ej: "maria-jose garcia" vs "maria jose garcia"
        name1_with_hyphens = name1.lower().strip()
        name2_with_hyphens = name2.lower().strip()
        
        if name1_with_hyphens.replace("-", " ") == name2_with_hyphens.replace("-", " "):
            return True
            
        return False

    def process_author_batch(self, batch_data):
        """Process a batch of authors to find similarities - MORE CONSERVATIVE."""
        author_ids, author_features, author_work_map = batch_data
        edges = []

        # Crear mapas para búsqueda rápida de nombres equivalentes
        name_groups = defaultdict(set)
        
        # Agrupar por nombre principal y todos los alias
        for author_id, features in author_features.items():
            normalized_name = features["normalized_name"]
            if normalized_name:
                # Agregar el nombre principal normalizado
                name_key = self.normalize_name_robust(normalized_name)
                name_groups[name_key].add(author_id)
                
                # Agregar todas las variaciones de alias
                for alt_name in features.get("alt_names", []):
                    if alt_name:
                        alt_key = self.normalize_name_robust(alt_name)
                        name_groups[alt_key].add(author_id)

        # Procesar grupos de nombres equivalentes
        for name_key, group_authors in name_groups.items():
            group_list = list(group_authors)
            if len(group_list) > 1:
                for i, a1 in enumerate(group_list):
                    for a2 in group_list[i+1:]:
                        if a1 != a2:
                            author1 = author_features[a1]
                            author2 = author_features[a2]

                            works1 = set(author_work_map.get(a1, []))
                            works2 = set(author_work_map.get(a2, []))
                            common_works = works1.intersection(works2)

                            should_merge, reason, confidence = self.should_consolidate(
                                author1, author2, common_works
                            )

                            if should_merge:
                                edges.append((a1, a2, reason, confidence))

        # Verificar pares restantes con alta similitud potencial
        processed_pairs = set()
        
        for a1, a2 in itertools.combinations(author_ids, 2):
            if (a1, a2) not in processed_pairs and (a2, a1) not in processed_pairs:
                author1 = author_features[a1]
                author2 = author_features[a2]
                
                # Solo verificar si tienen alta similitud potencial
                quick_sim = fuzz.ratio(author1["normalized_name"], author2["normalized_name"]) / 100.0
                if quick_sim >= 0.8:  # Solo procesar similitudes altas
                    works1 = set(author_work_map.get(a1, []))
                    works2 = set(author_work_map.get(a2, []))
                    common_works = works1.intersection(works2)

                    should_merge, reason, confidence = self.should_consolidate(
                        author1, author2, common_works
                    )

                    if should_merge:
                        edges.append((a1, a2, reason, confidence))
                
                processed_pairs.add((a1, a2))

        return edges

    def calculate_similarity(self, name1, name2):
        """Calculate similarity between names using multiple methods."""
        if not name1 or not name2:
            return 0.0
            
        norm1 = self.normalize_name_robust(name1)
        norm2 = self.normalize_name_robust(name2)
        
        # Si son equivalentes, máxima similitud
        if self.are_names_equivalent(name1, name2):
            return 1.0
        
        fuzzy_ratio = fuzz.ratio(norm1, norm2) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(norm1, norm2) / 100.0
        token_set_ratio = fuzz.token_set_ratio(norm1, norm2) / 100.0

        words1 = set(norm1.split())
        words2 = set(norm2.split())

        if len(words1) == 0 or len(words2) == 0:
            word_overlap = 0
        else:
            common_words = words1.intersection(words2)
            word_overlap = len(common_words) / max(len(words1), len(words2))

        # Similitud de iniciales
        initials1 = "".join(word[0] for word in words1 if word)
        initials2 = "".join(word[0] for word in words2 if word)

        if len(initials1) > 1 and len(initials2) > 1:
            initials_sim = fuzz.ratio(initials1, initials2) / 100.0
        else:
            initials_sim = 0.0

        # Pesos 
        combined_sim = (
            0.4 * fuzzy_ratio
            + 0.3 * token_sort_ratio
            + 0.2 * token_set_ratio
            + 0.1 * word_overlap
        )

        return combined_sim

    def extract_features(self, author_id, author_data, author_work_map):
        """Extract features for an author."""
        name = author_data.get("display_name", "")
        normalized_name = self.normalize_name_robust(name)

        alt_names = [
            self.normalize_name_robust(alt)
            for alt in author_data.get("display_name_alternatives", [])
            if alt
        ]

        works = author_work_map.get(author_id, [])

        affiliations = []
        institution_ids = set()
        countries = set()

        for affil in author_data.get("affiliations", []):
            institution = affil.get("institution", {})
            if institution:
                institution_id = institution.get("id", "").split("/")[-1]
                institution_name = institution.get("display_name", "")
                country_code = institution.get("country_code", "")

                if institution_id:
                    institution_ids.add(institution_id)
                if country_code:
                    countries.add(country_code)

                affiliations.append({
                    "institution_id": institution_id,
                    "institution_name": institution_name,
                    "country_code": country_code,
                    "years": affil.get("years", []),
                })
                
        for country in author_data.get("countries", []):
            countries.add(country)

        orcid = author_data.get("ids", {}).get("orcid", "")

        initials = ""
        if normalized_name:
            words = normalized_name.split()
            initials = "".join(word[0] for word in words if word)

        topics = []
        topic_ids = set()
        for topic in author_data.get("topics", []):
            topic_id = topic.get("id", "").split("/")[-1]
            topic_name = topic.get("display_name", "")
            if topic_id and topic_name:
                topics.append({"id": topic_id, "name": topic_name})
                topic_ids.add(topic_id)

        return {
            "id": author_id,
            "name": name,
            "normalized_name": normalized_name,
            "alt_names": alt_names,
            "initials": initials,
            "works_count": len(works),
            "cited_by_count": author_data.get("cited_by_count", 0),
            "works": works,
            "orcid": orcid,
            "affiliations": affiliations,
            "institution_ids": list(institution_ids),
            "countries": list(countries),
            "topics": topics,
            "topic_ids": list(topic_ids),
            "h_index": author_data.get("summary_stats", {}).get("h_index", 0),
            "x_concepts": author_data.get("x_concepts", []),
            "last_known_institutions": [
                inst.get("display_name", "")
                for inst in author_data.get("last_known_institutions", [])
            ],
        }

    def should_consolidate(self, author1, author2, common_works):
        """Determine if two authors should be consolidated - MORE CONSERVATIVE approach."""
        
        # REGLAS ESTRICTAS - Solo consolidar si estamos muy seguros
        
        # 1. ORCID idéntico - 100% confiable
        if (author1.get("orcid") and author2.get("orcid") and 
            author1["orcid"] == author2["orcid"]):
            return True, "same_orcid", 1.0

        # 2. Nombres exactamente equivalentes (incluyendo variaciones de guiones)
        if self.are_names_equivalent(author1["normalized_name"], author2["normalized_name"]):
            return True, "identical_name", 1.0

        # 3. Verificar nombres alternativos equivalentes - MUY IMPORTANTE
        for alt_name in author1.get("alt_names", []):
            if self.are_names_equivalent(alt_name, author2["normalized_name"]):
                return True, "alt_name_exact_match", 1.0
                
        for alt_name in author2.get("alt_names", []):
            if self.are_names_equivalent(author1["normalized_name"], alt_name):
                return True, "alt_name_exact_match", 1.0
                
        # 4. Verificar alias entre sí
        for alt1 in author1.get("alt_names", []):
            for alt2 in author2.get("alt_names", []):
                if self.are_names_equivalent(alt1, alt2):
                    return True, "alt_names_match", 1.0

        # 5. Calcular similitud de nombres
        name_sim = self.calculate_similarity(
            author1["normalized_name"], author2["normalized_name"]
        )

        # 6. CRÍTICO: Si comparten trabajos pero nombres muy diferentes, NO consolidar
        if len(common_works) > 0 and name_sim < 0.9:
            logger.warning(f"⚠️ Authors share works but have different names:")
            logger.warning(f"   - {author1['name']} vs {author2['name']}")
            logger.warning(f"   - Similarity: {name_sim:.2f}")
            logger.warning(f"   - Common works: {len(common_works)}")
            return False, "different_names_same_works", 0.0

        # 7. Si comparten trabajos Y tienen nombres similares
        if len(common_works) > 0 and name_sim >= 0.8:
            return True, "common_works_similar_names", min(0.95, name_sim + 0.1)

        # 8. Mismo país + nombres muy similares + misma institución
        same_country = bool(set(author1["countries"]).intersection(set(author2["countries"])))
        common_institutions = set(author1["institution_ids"]).intersection(
            set(author2["institution_ids"])
        )
        
        if (same_country and common_institutions and name_sim >= 0.85):
            return True, "same_country_institution_similar_name", min(0.9, name_sim + 0.05)

        # 9. Verificar similitud con nombres alternativos
        max_alt_sim = 0.0
        for alt_name in author1.get("alt_names", []):
            alt_sim = self.calculate_similarity(alt_name, author2["normalized_name"])
            max_alt_sim = max(max_alt_sim, alt_sim)
            
        for alt_name in author2.get("alt_names", []):
            alt_sim = self.calculate_similarity(author1["normalized_name"], alt_name)
            max_alt_sim = max(max_alt_sim, alt_sim)
            
        if max_alt_sim >= 0.9:
            return True, "high_alt_name_similarity", max_alt_sim

        # 10. Nombres muy similares + mismo ORCID parcial o mismas instituciones principales
        if name_sim >= 0.9:
            if common_institutions:
                return True, "very_similar_name_same_institution", name_sim
            
        # - No consolidar en casos dudosos
        return False, "insufficient_evidence", name_sim

    def find_candidates(self, authors_features, author_work_map):
        """Find candidates for consolidation by comparing all pairs of authors (N*N)."""
        logger.info("🔍 Starting N*N author consolidation. This may take a while for large datasets...")

        G = nx.Graph()
        total_authors = len(authors_features)
        edges_added = 0

        for author_id, features in authors_features.items():
            G.add_node(author_id, **features)

        all_author_ids = list(authors_features.keys())
        
        # Iterar sobre todas las combinaciones únicas de pares de autores
        for i, author_id1 in enumerate(tqdm(all_author_ids, desc="Processing author pairs")):
            for j in range(i + 1, len(all_author_ids)):
                author_id2 = all_author_ids[j]

                author1_data = authors_features[author_id1]
                author2_data = authors_features[author_id2]

                works1 = set(author_work_map.get(author_id1, []))
                works2 = set(author_work_map.get(author_id2, []))
                common_works = works1.intersection(works2)

                should_merge, reason, confidence = self.should_consolidate(
                    author1_data, author2_data, common_works
                )

                if should_merge:
                    if not G.has_edge(author_id1, author_id2):
                        G.add_edge(author_id1, author_id2, reason=reason, confidence=confidence)
                        edges_added += 1
                        logger.debug(f"🔗 Consolidating authors ({reason}, conf: {confidence:.3f}):")
                        logger.debug(f"   - {author1_data['name']} (ID: {author_id1})")
                        logger.debug(f"   - {author2_data['name']} (ID: {author_id2})")
                        if common_works:
                            logger.debug(f"   📚 Shared articles: {len(common_works)}")
        
        logger.info(f"✅ N*N consolidation completed: {edges_added} high-confidence connections found among {total_authors} authors")
        return G
