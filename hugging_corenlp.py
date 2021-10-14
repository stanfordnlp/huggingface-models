"""
This script allows for pushing of the corenlp models to N different huggingface repos.

Generously provided by Omar Sanseviero

huggingface-cli login
python hugging_corenlp.py --input_dir <models_path>  --branch <version>
"""

import argparse
import datetime
import os
import shutil

from huggingface_hub import  Repository, HfApi, HfFolder

def get_model_card(lang):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    model_card = """---
tags:
- corenlp
library_tag: corenlp
language:
- {lang}
license: gpl-2.0
---
# Core NLP model for {lang}
CoreNLP is your one stop shop for natural language processing in Java! CoreNLP enables users to derive linguistic annotations for text, including token and sentence boundaries, parts of speech, named entities, numeric and time values, dependency and constituency parses, coreference, sentiment, quote attributions, and relations.
Find more about it in [our website](https://stanfordnlp.github.io/CoreNLP) and our [GitHub repository](https://github.com/stanfordnlp/CoreNLP).

Last updated {now}
""".format(lang=lang, now=now)
    return model_card

MODELS = {   # the value is a potential alternate name for the file
    "arabic":           "stanford-arabic-corenlp-models-current.jar",
    "chinese":          "stanford-chinese-corenlp-models-current.jar",
    "english-default":  "stanford-corenlp-models-current.jar",
    "english-extra":    "stanford-english-corenlp-models-current.jar",
    "english-kbp":      "stanford-english-kbp-corenlp-models-current.jar",
    "french":           "stanford-french-corenlp-models-current.jar",
    "german":           "stanford-german-corenlp-models-current.jar",
    "hungarian":        "stanford-hungarian-corenlp-models-current.jar",
    "italian":          "stanford-italian-corenlp-models-current.jar",
    "spanish":          "stanford-spanish-corenlp-models-current.jar",
}

def write_model_card(repo_local_path, model):
    """
    Write a README for the current model to the given path
    """
    readme_path = os.path.join(repo_local_path, "README.md")
    with open(readme_path, "w") as f:
        f.write(get_model_card(model))

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input_dir', type=str, default=None, help='Directory for loading the CoreNLP models')
    parser.add_argument('--version', type=str, default="4.3.0", help='Version of corenlp models to upload')
    args = parser.parse_args()
    return args


def push_to_hub():
    args = parse_args()
    input_dir = args.input_dir

    api = HfApi()

    for model in MODELS.keys():
        # Create the repository
        repo_name = "corenlp-" + model
        repo_url = api.create_repo(
            name=repo_name,
            token=HfFolder.get_token(),
            organization="stanfordnlp",
            exist_ok=True,
        )

        # Clone the repository
        repo_local_path = os.path.join("hub", repo_name)

        repo = Repository(repo_local_path, clone_from=repo_url)
        # checkout "main" so that we know we are tracking files correctly
        repo.git_checkout("main")
        repo.git_pull(rebase=True)

        # Make sure jar files are tracked with LFS
        repo.lfs_track(["*.jar"])
        repo.push_to_hub(commit_message="Update tracked files", clean_ok=True)

        # Create a copy of the jar file in the repository
        src = f"stanford-corenlp-models-{model}.jar"
        dst = os.path.join(repo_local_path, src)
        if input_dir:
            src = os.path.join(input_dir, src)
        if not os.path.exists(src):
            if input_dir:
                new_src = os.path.join(input_dir, MODELS[model])
            else:
                new_src = MODELS[model]
            if not os.path.exists(new_src):
                raise FileNotFoundError(f"Cannot find {model} model.  Looked for {src} and {new_src}")
            src = new_src
        shutil.copy(src, dst)

        # Create the model card
        write_model_card(repo_local_path, model)

        # Push the model
        # note: the error of not having anything to push will hopefully
        # never happen since the README is updated to the millisecond
        print("Pushing files to the Hub")
        repo.push_to_hub(commit_message=f"Add model for version {args.version}")

        tag = "v" + args.version
        if repo.tag_exists(tag):
            repo.delete_tag(tag, remote="origin")
        repo.add_tag(tag_name=tag, message=f"Adding new version of models {tag}", remote="origin")
        print(f"Added a tag for the new models: {tag}")

        print(f"View your model in {repo_url}")


if __name__ == '__main__':
    push_to_hub()
