import numpy as np
from typing import List, Tuple
from sklearn.metrics.pairwise import cosine_similarity


class SimilarityService:
    """
    Computes vector similarity metrics (cosine similarity, centroid vectors,
    pairwise distance matrices) for market trend analysis.
    """

    @staticmethod
    def compute_cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
        """
        Calculates cosine similarity between two single vectors.
        Returns value in [-1.0, 1.0], typically [0.0, 1.0] for non-negative embeddings.
        """
        a = np.array(vec1, dtype=np.float32)
        b = np.array(vec2, dtype=np.float32)
        norm_a = np.linalg.norm(a)
        norm_b = np.linalg.norm(b)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a, b) / (norm_a * norm_b))

    @staticmethod
    def compute_similarity_matrix(vectors: List[List[float]]) -> np.ndarray:
        """
        Calculates full pairwise cosine similarity matrix (N x N) for a list of vectors.
        """
        if not vectors:
            return np.zeros((0, 0), dtype=np.float32)
        matrix = np.array(vectors, dtype=np.float32)
        return cosine_similarity(matrix)

    @staticmethod
    def compute_centroid(vectors: List[List[float]]) -> List[float]:
        """
        Computes the normalized average centroid vector for a cluster of vectors.
        """
        if not vectors:
            return []
        arr = np.array(vectors, dtype=np.float32)
        mean_vec = np.mean(arr, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
        return mean_vec.tolist()

    @staticmethod
    def compute_coherence(vectors: List[List[float]]) -> float:
        """
        Calculates internal semantic coherence as the mean pairwise cosine similarity
        among all pairs in the cluster.
        """
        n = len(vectors)
        if n <= 1:
            return 1.0
        sim_matrix = SimilarityService.compute_similarity_matrix(vectors)
        # Take upper triangle without diagonal
        upper_indices = np.triu_indices(n, k=1)
        pairwise_sims = sim_matrix[upper_indices]
        return float(np.mean(pairwise_sims))
