#!/usr/bin/env bash
python3 ./train_model.py -t parlai_tasks.paraphrases.agents \
                         -m parlai_agents.paraphraser.paraphraser:ParaphraserAgent \
                         -mf /tmp/paraphraser \
                         --batchsize 16 \
                         --display-examples True \
                         --max-train-time 10\
                         --embedding_file 'yalen_sg_word_vectors_300.txt'\
                         --model_file 'tmp/my_model'