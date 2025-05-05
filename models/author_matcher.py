import networkx as nx
import numpy as np
import logging
import itertools
from collections import defaultdict
from tqdm import tqdm
from rapidfuzz import fuzz
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import DBSCAN

from utils.text_processing import normalize_name

logger = logging.getLogger(__name__)


class SmartAuthorMatcher:
    """Enhanced class to manage author consolidation using advanced ML techniques."""

    def __init__(self, similarity_threshold=0.85, batch_size=1000):
        """Initialize the vectorizer and similarity parameters."""
        logger.info("🔍 Initializing advanced author consolidation system...")
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

        self.eps = 0.2
        self.min_samples = 1

        logger.info("✅ Advanced consolidation system initialized correctly")

    def process_author_batch(self, batch_data):
        """Process a batch of authors to find similarities."""
        author_ids, author_features, author_work_map = batch_data
        edges = []

        names = [
            features["normalized_name"]
            for features in author_features.values()
            if features["normalized_name"]
        ]

        if not names:
            return edges

        try:
            char_vectors = self.char_vectorizer.fit_transform(names)
            word_vectors = self.word_vectorizer.fit_transform(names)

            vectors_normalized = np.hstack(
                [char_vectors.toarray() * 0.5, word_vectors.toarray() * 0.5]
            )

            clustering = DBSCAN(
                eps=self.eps, min_samples=self.min_samples, metric="cosine"
            ).fit(vectors_normalized)

            labels = clustering.labels_

            name_to_id = {}
            for author_id, features in author_features.items():
                if features["normalized_name"] in names:
                    name_to_id[features["normalized_name"]] = author_id

            clusters = defaultdict(list)
            for i, label in enumerate(labels):
                if label != -1:
                    name = names[i]
                    author_id = name_to_id.get(name)
                    if author_id:
                        clusters[label].append(author_id)

            for cluster_id, cluster_authors in clusters.items():
                if len(cluster_authors) > 1:
                    for a1, a2 in itertools.combinations(cluster_authors, 2):
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

            for a1, author1 in author_features.items():
                for alt_name in author1.get("alt_names", []):
                    if not alt_name:
                        continue

                    for a2, author2 in author_features.items():
                        if a1 == a2:
                            continue

                        if author2["normalized_name"]:
                            alt_sim = self.calculate_similarity(
                                alt_name, author2["normalized_name"]
                            )
                            if alt_sim >= self.similarity_threshold:
                                edges.append((a1, a2, "alt_name_match", alt_sim))
                                break

            for a1, a2 in itertools.combinations(author_ids, 2):
                author1 = author_features[a1]
                author2 = author_features[a2]

                id1_parts = author1["id"].lower().split("/")
                id2_parts = author2["id"].lower().split("/")

                if (
                    len(id1_parts) > 1
                    and len(id2_parts) > 1
                    and id1_parts[-1] == id2_parts[-1]
                ):
                    name_sim = self.calculate_similarity(
                        author1["normalized_name"], author2["normalized_name"]
                    )
                    if name_sim > 0.6:
                        edges.append((a1, a2, "similar_id", name_sim))

        except Exception as e:
            logger.error(f"Error in batch processing: {e}")

        return edges

    def calculate_similarity(self, name1, name2):
        """Calculate similarity between names using multiple methods."""
        fuzzy_ratio = fuzz.ratio(name1, name2) / 100.0
        token_sort_ratio = fuzz.token_sort_ratio(name1, name2) / 100.0
        token_set_ratio = fuzz.token_set_ratio(name1, name2) / 100.0

        words1 = set(name1.split())
        words2 = set(name2.split())

        if len(words1) == 0 or len(words2) == 0:
            word_overlap = 0
        else:
            common_words = words1.intersection(words2)
            word_overlap = len(common_words) / max(len(words1), len(words2))

        initials1 = "".join(word[0] for word in words1 if word)
        initials2 = "".join(word[0] for word in words2 if word)

        if len(initials1) > 1 and len(initials2) > 1:
            initials_sim = fuzz.ratio(initials1, initials2) / 100.0
        else:
            initials_sim = 0.0

        combined_sim = (
            0.3 * fuzzy_ratio
            + 0.2 * token_sort_ratio
            + 0.2 * token_set_ratio
            + 0.2 * word_overlap
            + 0.1 * initials_sim
        )

        return combined_sim

    def extract_features(self, author_id, author_data, author_work_map):
        """Extract features for an author."""
        name = author_data.get("display_name", "")
        normalized_name = normalize_name(name)
        alt_names = [
            normalize_name(alt)
            for alt in author_data.get("display_name_alternatives", [])
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

                affiliations.append(
                    {
                        "institution_id": institution_id,
                        "institution_name": institution_name,
                        "country_code": country_code,
                        "years": affil.get("years", []),
                    }
                )
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
        """Determine if two authors should be consolidated based on features and similarity."""
        # 1. If they have common works
        if len(common_works) > 0:
            return True, "common_works", 1.0

        # 2. Same ORCID
        if (
            author1.get("orcid")
            and author2.get("orcid")
            and author1["orcid"] == author2["orcid"]
        ):
            return True, "same_orcid", 1.0

        # 3. Name similarity
        name_sim = self.calculate_similarity(
            author1["normalized_name"], author2["normalized_name"]
        )

        # 4. If they are from the same country
        same_country = bool(
            set(author1["countries"]).intersection(set(author2["countries"]))
        )

        # If they are from the same country with high name similarity
        if same_country and name_sim > 0.8:
            return True, "same_country_and_name", min(0.95, name_sim + 0.25)

        # If they are from the same country with moderate name similarity
        if same_country and name_sim > 0.6:
            return True, "same_country_and_moderate_name", min(0.9, name_sim + 0.2)

        # 5. Similar IDs
        id1_parts = author1["id"].lower().split("/")
        id2_parts = author2["id"].lower().split("/")

        if len(id1_parts) > 1 and len(id2_parts) > 1:
            if id1_parts[-1] == id2_parts[-1]:
                if name_sim > 0.6:
                    return True, "similar_id", name_sim

        # 6. Same initials and sufficiently similar names
        if (
            author1["initials"]
            and author2["initials"]
            and author1["initials"] == author2["initials"]
        ):
            if len(author1["initials"]) > 1 and name_sim > 0.7:
                return True, "matching_initials", name_sim

        # 7. Alternative names
        for alt_name in author1["alt_names"]:
            if not alt_name:
                continue
            alt_sim = self.calculate_similarity(alt_name, author2["normalized_name"])
            if alt_sim >= self.similarity_threshold:
                return True, "alt_name_match", alt_sim

        for alt_name in author2["alt_names"]:
            if not alt_name:
                continue
            alt_sim = self.calculate_similarity(author1["normalized_name"], alt_name)
            if alt_sim >= self.similarity_threshold:
                return True, "alt_name_match", alt_sim

        # 8. Common institutions
        common_institutions = set(author1["institution_ids"]).intersection(
            set(author2["institution_ids"])
        )
        if common_institutions and name_sim > 0.6:
            # If they are also from the same country
            bonus = 0.3 if same_country else 0.2
            return True, "common_institutions", min(0.9, name_sim + bonus)

        # 9. Common research topics
        common_topics = set(author1["topic_ids"]).intersection(
            set(author2["topic_ids"])
        )
        if common_topics and name_sim > 0.6:
            # If they are also from the same country
            bonus = 0.25 if same_country else 0.15
            return True, "common_topics", min(0.85, name_sim + bonus)

        # 10. Common concepts
        concepts1 = {c["id"] for c in author1.get("x_concepts", [])}
        concepts2 = {c["id"] for c in author2.get("x_concepts", [])}
        common_concepts = concepts1.intersection(concepts2)
        if common_concepts and name_sim > 0.6:
            # Give more weight if they are also from the same country
            bonus = 0.2 if same_country else 0.1
            return True, "common_concepts", min(0.85, name_sim + bonus)

        # 11. Similar h-index
        if (
            abs(author1.get("h_index", 0) - author2.get("h_index", 0)) <= 3
            and name_sim > 0.7
        ):
            # Give more weight if they are also from the same country
            bonus = 0.15 if same_country else 0.05
            return True, "similar_h_index", min(0.8, name_sim + bonus)

        # 12. If they are from the same country but with low name similarity, consider with lower confidence
        if same_country and name_sim > 0.5:
            return True, "same_country_weak_name", min(0.7, name_sim + 0.1)

        return False, "no_match", 0.0

    def find_candidates(self, authors_features, author_work_map):
        """Find candidates for consolidation using an advanced clustering approach."""
        logger.info(
            "🔍 Looking for consolidation candidates using advanced clustering..."
        )

        G = nx.Graph()
        total_authors = len(authors_features)
        edges_added = 0

        for author_id, features in authors_features.items():
            G.add_node(author_id, **features)

        all_author_ids = list(authors_features.keys())
        batch_size = min(self.batch_size, len(all_author_ids))

        logger.info("Creating smart batches for sequential processing...")

        work_to_authors = defaultdict(list)
        for author_id, features in authors_features.items():
            for work_id in author_work_map.get(author_id, []):
                work_to_authors[work_id].append(author_id)

        work_batches = defaultdict(set)
        for work_id, related_authors in work_to_authors.items():
            if len(related_authors) > 1:
                batch_id = len(work_batches)
                work_batches[batch_id].update(related_authors)

        processed_authors = set()
        smart_batches = []

        for author_set in work_batches.values():
            if len(author_set) > 1:
                batch = {}
                for author_id in author_set:
                    if author_id in authors_features:
                        batch[author_id] = authors_features[author_id]
                        processed_authors.add(author_id)

                if batch:
                    smart_batches.append((list(batch.keys()), batch, author_work_map))

        remaining_authors = [a for a in all_author_ids if a not in processed_authors]

        if remaining_authors:
            remaining_names = [
                authors_features[a]["normalized_name"]
                for a in remaining_authors
                if authors_features[a]["normalized_name"]
            ]
            name_to_id = {
                authors_features[a]["normalized_name"]: a
                for a in remaining_authors
                if authors_features[a]["normalized_name"]
            }

            if remaining_names:
                try:
                    name_vectors = self.char_vectorizer.fit_transform(remaining_names)

                    clustering = DBSCAN(eps=0.4, min_samples=1, metric="cosine").fit(
                        name_vectors
                    )
                    labels = clustering.labels_

                    cluster_to_authors = defaultdict(list)
                    for i, label in enumerate(labels):
                        name = remaining_names[i]
                        author_id = name_to_id.get(name)
                        if author_id:
                            cluster_to_authors[label].append(author_id)

                    for cluster_authors in cluster_to_authors.values():
                        batch = {}
                        for author_id in cluster_authors:
                            batch[author_id] = authors_features[author_id]
                        smart_batches.append(
                            (list(batch.keys()), batch, author_work_map)
                        )

                except Exception as e:
                    logger.error(f"Error in smart batch creation: {e}")
                    for i in range(0, len(remaining_authors), batch_size):
                        batch_ids = remaining_authors[i : i + batch_size]
                        batch = {a: authors_features[a] for a in batch_ids}
                        smart_batches.append((batch_ids, batch, author_work_map))
            else:
                for i in range(0, len(remaining_authors), batch_size):
                    batch_ids = remaining_authors[i : i + batch_size]
                    batch = {a: authors_features[a] for a in batch_ids}
                    smart_batches.append((batch_ids, batch, author_work_map))

        logger.info(f"Processing {len(smart_batches)} batches sequentially...")

        all_edges = []
        for batch_data in tqdm(smart_batches, desc="Processing batches"):
            batch_edges = self.process_author_batch(batch_data)
            all_edges.extend(batch_edges)

        for a1, a2, reason, confidence in all_edges:
            if not G.has_edge(a1, a2):
                G.add_edge(a1, a2, reason=reason, confidence=confidence)
                edges_added += 1

                if edges_added % 100 == 0 or confidence > 0.95:
                    logger.info(
                        f"🔄 Joining authors ({reason}, conf: {confidence:.2f}):"
                    )
                    logger.info(f"   - {authors_features[a1]['name']} (ID: {a1})")
                    logger.info(f"   - {authors_features[a2]['name']} (ID: {a2})")

                    works1 = set(author_work_map.get(a1, []))
                    works2 = set(author_work_map.get(a2, []))
                    common_works = works1.intersection(works2)
                    if common_works:
                        logger.info(f"   ⚠️  Shared articles: {len(common_works)}")

        logger.info(
            f"✅ Advanced consolidation completed: {edges_added} connections found among {total_authors} authors"
        )
        return G
