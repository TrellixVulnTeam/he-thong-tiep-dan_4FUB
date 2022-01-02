from chatterbot.comparisons import Comparator


class VietnameseJaccardSimilarity(Comparator):
    """
    Calculates the similarity of two statements based on the Jaccard index.
    The Jaccard index is composed of a numerator and denominator.
    In the numerator, we count the number of items that are shared between the sets.
    In the denominator, we count the total number of items across both sets.
    Let's say we define sentences to be equivalent if 50% or more of their tokens are equivalent.
    Here are two sample sentences:
        The young cat is hungry.
        The cat is very hungry.
    When we parse these sentences to remove stopwords, we end up with the following two sets:
        {young, cat, hungry}
        {cat, very, hungry}
    In our example above, our intersection is {cat, hungry}, which has count of two.
    The union of the sets is {young, cat, very, hungry}, which has a count of four.
    Therefore, our `Jaccard similarity index`_ is two divided by four, or 50%.
    Given our similarity threshold above, we would consider this to be a match.
    .. _`Jaccard similarity index`: https://en.wikipedia.org/wiki/Jaccard_index
    """

    def compare(self, statement_a, statement_b):
        """
        Return the calculated similarity of two
        statements based on the Jaccard index.
        """
        statement_a_lemmas = set(statement_a.search_text.split(' '))
        statement_b_lemmas = set(statement_b.search_text.split(' '))

        # Calculate Jaccard similarity
        numerator = len(statement_a_lemmas.intersection(statement_b_lemmas))
        denominator = float(len(statement_a_lemmas.union(statement_b_lemmas)))
        ratio = numerator / denominator

        if any(a_tags in statement_b.get_tags()
               for a_tags in statement_a.get_tags()) and ratio < 0.95:
            ratio += 0.05

        return ratio


class VietnameseCosineSimilarity(Comparator):
    """
    Calculates the similarity of two statements based on the Cosine Similarity
    Step 1: We convert statement to tf-idf vector
    Step 2: Caculate similarity base on consine similarity 
    """

    def compare(self, statement_a, statement_b):
        """
        Return the calculated similarity of two
        statements based on the cosine similarity.
        """
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity

        # Caculate tfidf cosine similarity
        tfidf = TfidfVectorizer(token_pattern=r'\S+')
        content = [
            ' '.join(statement_a.search_text),
            ' '.join(statement_b.search_text)
        ]
        matrix = tfidf.fit_transform(content)
        confidence = cosine_similarity(matrix[0], matrix[1])[0][0]

        # If any statement has oldtags value, add 5% confidence to it
        if any(a_tags in statement_b.get_tags()
               for a_tags in statement_a.get_tags()) and confidence < 0.95:
            confidence += 0.05

        return np.round(confidence, 4)
