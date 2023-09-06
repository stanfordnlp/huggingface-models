"""
This script allows for pushing of the corenlp models to N different huggingface repos.

Generously provided by Omar Sanseviero

huggingface-cli login
python3 hugging_corenlp.py --input_dir <models_path>  --branch <version>
"""

import argparse
import datetime
import os
import shutil

from collections import namedtuple

from huggingface_hub import  HfApi, HfFolder, hf_hub_download

def get_model_card(lang, model):
    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    model_card = """---
tags:
- corenlp
library_tag: corenlp
language: {lang}
license: gpl-2.0
---
# Core NLP model for {model}
CoreNLP is your one stop shop for natural language processing in Java! CoreNLP enables users to derive linguistic annotations for text, including token and sentence boundaries, parts of speech, named entities, numeric and time values, dependency and constituency parses, coreference, sentiment, quote attributions, and relations.
Find more about it in [our website](https://stanfordnlp.github.io/CoreNLP) and our [GitHub repository](https://github.com/stanfordnlp/CoreNLP).

This card and repo were automatically prepared with `hugging_corenlp.py` in the `stanfordnlp/huggingface-models` repo

Last updated {now}
""".format(lang=lang, model=model, now=now)
    return model_card

# lang is an abbrev to use in the model card
# local_name is a potential alternate name for the file
# remote_name is the name to use when pushing remotely
# repo_name is the repo name if corenlp-model is not suitable for some reason
Model = namedtuple("Model", 'model_name, lang, local_name, remote_name, repo_name')

MODELS = [
    Model("CoreNLP",          "en",   "stanford-corenlp-latest.zip",                     "stanford-corenlp-latest.zip", "CoreNLP"),
    Model("arabic",           "ar",   "stanford-arabic-corenlp-models-current.jar",      None,                          None),
    Model("chinese",          "zh",   "stanford-chinese-corenlp-models-current.jar",     None,                          None),
    Model("english-default",  "en",   "stanford-corenlp-models-current.jar",             None,                          None),
    Model("english-extra",    "en",   "stanford-english-corenlp-models-current.jar",     None,                          None),
    Model("english-kbp",      "en",   "stanford-english-kbp-corenlp-models-current.jar", None,                          None),
    Model("french",           "fr",   "stanford-french-corenlp-models-current.jar",      None,                          None),
    Model("german",           "de",   "stanford-german-corenlp-models-current.jar",      None,                          None),
    Model("hungarian",        "hu",   "stanford-hungarian-corenlp-models-current.jar",   None,                          None),
    Model("italian",          "it",   "stanford-italian-corenlp-models-current.jar",     None,                          None),
    Model("spanish",          "es",   "stanford-spanish-corenlp-models-current.jar",     None,                          None),
]

def write_model_card(repo_local_path, lang, model):
    """
    Write a README for the current model to the given path
    """
    readme_path = os.path.join(repo_local_path, "README.md")
    with open(readme_path, "w") as f:
        f.write(get_model_card(lang, model))

def parse_args():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # "/home/john/extern_data/corenlp/"
    parser.add_argument('--input_dir', type=str, default="/u/nlp/data/StanfordCoreNLPModels", help='Directory for loading the CoreNLP models')
    # "/home/john/huggingface/hub"
    parser.add_argument('--output_dir', type=str, default="/u/nlp/software/hub", help='Directory with the repos')
    parser.add_argument('--version', type=str, default="4.5.4", help='Version of corenlp models to upload')
    parser.add_argument('--no_models', dest="models", action='store_false', default=True, help="Only push the package without updating the models.  Useful for when a new version is released, with only code changes, and the 'latest' symlink wasn't properly updated")
    args = parser.parse_args()
    return args


def maybe_add_lfs(api, repo_id, repo_local_path, extension):
    # read the existing .gitattributes file
    git_filename = os.path.join(repo_local_path, ".gitattributes")
    with open(git_filename) as fin:
        lines = fin.readlines()

    # if the extension isn't already there, add it and push the new version
    if not any(line.startswith(extension + " ") for line in lines):
        lines.append("%s filter=lfs diff=lfs merge=lfs -text\n" % extension)
        blob = "".join(lines).encode()
        api.upload_file(repo_id=repo_id, path_in_repo=".gitattributes", path_or_fileobj=blob)

def push_to_hub():
    args = parse_args()
    api = HfApi()

    input_dir = args.input_dir
    if args.models:
        stuff_to_push = MODELS
    else:
        stuff_to_push = [x for x in MODELS if x.model_name == 'CoreNLP']

    for model in stuff_to_push:
        # Create the repository
        lang = model.lang
        model_name = model.model_name
        repo_name = model.repo_name if model.repo_name else "corenlp-%s" % model_name
        repo_id = "stanfordnlp/" + repo_name
        repo_url = api.create_repo(
            repo_id=repo_id,
            exist_ok=True,
        )

        # check the lfs status of .zip and .jar
        # TODO: we can probably get rid of repo_local_path
        # - use a temporary file for .gitattributes
        # - use a bytes blob for the README
        # - use the jar / zip file for CoreNLP directly, wherever it is
        repo_local_path = os.path.join(args.output_dir, repo_name)
        hf_hub_download(repo_id, ".gitattributes", local_dir=repo_local_path, local_dir_use_symlinks=False)
        maybe_add_lfs(api, repo_id, repo_local_path, '*.jar')
        maybe_add_lfs(api, repo_id, repo_local_path, '*.zip')

        # Create a copy of the jar file in the repository
        dst = os.path.join(repo_local_path, model.remote_name) if model.remote_name else os.path.join(repo_local_path, f"stanford-corenlp-models-{model_name}.jar")
        src_candidates = [f"stanford-corenlp-models-{model_name}.jar",
                          model.local_name,
                          # stanford-corenlp-4.4.0-models-arabic.jar
                          f"stanford-corenlp-{args.version}-models-{model_name}.jar"]
        for src in src_candidates:
            if input_dir:
                src = os.path.join(input_dir, src)
            if os.path.exists(src):
                break
        else:
            if input_dir:
                locations_searched = ", ".join(os.path.join(input_dir, src) for src in src_candidates)
            else:
                locations_searched = ", ".join(src_candidates)
            raise FileNotFoundError(f"Cannot find {model_name} model.  Looked in {locations_searched}")
        print(f"Copying model from {src} to {dst}")
        shutil.copy(src, dst)

        # Create the model card
        write_model_card(repo_local_path, lang, model_name)

        # Upload model + model card
        # setting delete_patterns will clean up old model files as we go
        # note: the error of not having anything to push will hopefully
        # never happen since the README is updated to the millisecond
        print("Pushing files to the Hub from %s to %s" % (repo_local_path, repo_id))
        api.upload_folder(repo_id=repo_id, folder_path=repo_local_path, commit_message=f"Add model {args.version}")

        # Check and delete tag if already exist
        new_tag_name = "v" + args.version
        refs = api.list_repo_refs(repo_id=repo_id)
        for tag in refs.tags:
            if tag.name == new_tag_name:
                api.delete_tag(repo_id=repo_id, tag=new_tag_name)
                break

        # Tag model version
        api.create_tag(repo_id=repo_id, tag=new_tag_name, tag_message=f"Adding new version of models {new_tag_name}")
        print(f"Added a tag for the new models: {new_tag_name}")

        print(f"View your model in {repo_url}")


if __name__ == '__main__':
    push_to_hub()
