import json
import openai
import pickle
import numpy as np
from tqdm import tqdm


def embed(text):
    text = text.replace("\n", " ")
    return openai.Embedding.create(
        input=[text], model="text-embedding-ada-002")["data"][0]["embedding"]


def initialize_cache(first=False):
    data = json.load(open("qualia-san/qualia-san.json"))
    if first:
        cache = {}
    else:
        cache = pickle.load(open("qualia-vector.pickle", "rb"))
    for x in data:
        body = x["body"]
        if body in cache:
            continue
        cache[body] = embed(body)
        print(body)

    pickle.dump(cache, open("qualia-vector.pickle", "wb"))


def update_cache():
    data = json.load(open("qualia-san/qualia-san.json"))
    vs = VectorStore()
    for x in data:
        body = x["body"]
        vs.get_or_make(body)
        print(body)


class VectorStore:
    def __init__(self):
        self.cache = pickle.load(open("qualia-vector.pickle", "rb"))

    def get_or_make(self, body):
        if body not in self.cache:
            self.cache[body] = embed(body)
            pickle.dump(self.cache, open("qualia-vector.pickle", "wb"))
        return self.cache[body]

    def get_sorted(self, query):
        q = np.array(embed(query))
        buf = []
        for body, v in tqdm(self.cache.items()):
            buf.append((q.dot(v), body))
        buf.sort(reverse=True)
        return buf
