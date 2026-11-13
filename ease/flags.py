"""The team's soft-fail flag definitions, copied unchanged from DTSC3602_Models/Steam_EASE_Safe_Recommender/team_eval/evaluate.py
(RShea42/DTSC3602_Models @ e8f7531), so the app flags games exactly the way the shared scoring does."""
import numpy as np
import pandas as pd
import scipy.sparse as sp

NEG = {"Mostly Negative", "Negative", "Very Negative", "Overwhelmingly Negative"}


def tag_matrix(games):
    """Row-normalized multi-hot of each game's first 10 user tags (genres if no tags), over the 400 most common tags."""
    lists = [list(t)[:10] if t is not None and len(t) else (list(g)[:10] if g is not None else [])
             for t, g in zip(games.tags, games.genres)]
    vocab = pd.Series([x for l in lists for x in l]).value_counts().index[:400]
    col = pd.Series(np.arange(len(vocab)), index=vocab)
    r, c = [], []
    for i, l in enumerate(lists):
        for x in l:
            if x in col.index:
                r.append(i); c.append(col[x])
    M = sp.csr_matrix((np.ones(len(r), np.float32), (r, c)), shape=(len(games), len(vocab)))
    n = np.sqrt(np.asarray(M.multiply(M).sum(1)).ravel()); n[n == 0] = 1
    return sp.diags(1 / n) @ M
