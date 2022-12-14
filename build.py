from pybuilder.core import use_plugin, init, task, depends, description
import os
import build_utils as bu

use_plugin('python.core')
use_plugin('python.unittest')
use_plugin('python.install_dependencies')

default_task = 'build'


def create_dir(dir):
    os.makedirs('build/' + dir, mode=0o755, exist_ok=True)


@init
def set_properties(project):
    import sys
    cwd = os.getcwd()
    sys.path.append(cwd)
    os.environ['EMBEDDINGS_URL'] = os.getenv('EMBEDDINGS_URL',
                                             default='http://share.ipavlov.mipt.ru:8080/repository/embeddings/')
    os.environ['MODELS_URL'] = os.getenv('MODELS_URL',
                                         default='http://share.ipavlov.mipt.ru:8080/repository/models/')
    os.environ['DATASETS_URL'] = os.getenv('DATASETS_URL',
                                           default='http://share.ipavlov.mipt.ru:8080/repository/datasets/')
    os.environ['KERAS_BACKEND'] = os.getenv('KERAS_BACKEND', default='tensorflow')

    project.set_property('dir_source_main_python', '.')
    project.set_property('dir_source_unittest_python', 'tests')
    project.depends_on_requirements('requirements.txt')


@task
def build():
    pass


@task
def clean():
    import shutil
    shutil.rmtree('./build', ignore_errors=True)


@task(description="upload archived model to the Nexus repository")
@depends("archive_model")
def upload_model_to_nexus(project):
    """
    Use 'pyb -P model_name="<model_name>" upload_model_to_nexus' to upload archived model to Nexus repository
    of the lab. If model_name == 'deeppavlov_docs', then documentation from build/docs will be archived and uploaded.
    archive_model task will be executed before.
    """
    import requests, datetime
    os.chdir('build')
    model_name = project.get_property('model_name')
    file_name = model_name + '_' + datetime.date.today().strftime("%y%m%d") + '.tar.gz'
    url = 'http://share.ipavlov.mipt.ru:8080/repository/'
    url += 'docs/' if model_name == 'deeppavlov_docs' else 'models/'
    headers = {'Content-Type': 'application/binary'}
    with open(file_name, 'rb') as artifact:
        requests.put(url + model_name + '/' + file_name, headers=headers,
                     data=artifact, auth=('jenkins', 'jenkins123'))


@task
@description("Pack a model to model_name_CURRENTDATE.tar.gz")
def archive_model(project):
    """
    Use 'pyb -P model_name="<model_name>" archive_model' to create '<model_name>_CURRENTDATE.tar.gz'
    in 'build' directory. If model_name == 'deeppavlov_docs', then documentation from build/docs will be archived.
    """
    import tarfile, datetime
    os.chdir('build')
    model_name = project.get_property('model_name')
    archive_name = model_name + '_' + datetime.date.today().strftime("%y%m%d")

    if model_name == 'deeppavlov_docs':
        import shutil
        shutil.make_archive(archive_name, 'gztar', 'docs', 'deeppavlov')
        os.chdir('..')
        return

    with tarfile.open(archive_name + '.tar.gz', "w:gz") as archive:
        os.chdir(model_name)
        for f in os.listdir('.'):
            if os.path.isfile(f) and (('h5' in f) or ('json' in f) or ('pkl' in f)or ('dict' in f) or ('threshold' in f)
                                      or ('data' in f) or ('index' in f) or ('meta' in f) or ('checkpoint' in f)):
                archive.add(f)
        os.chdir('..')
    os.chdir('..')


@task(description="train all models")
@depends("train_paraphraser", "train_ner", "train_insults",
         "train_coreference", "train_coref", "train_squad")
def train_models():
    pass


@task
def train_paraphraser(project):
    create_dir('paraphraser')
    num_epochs = '5' if project.get_property('idle_train') == 'True' else '-1'
    metrics = bu.model(['-t', 'deeppavlov.tasks.paraphrases.agents',
                        '-m', 'deeppavlov.agents.paraphraser.paraphraser:ParaphraserAgent',
                        '-mf', './build/paraphraser/paraphraser',
                        '--datatype', 'train:ordered',
                        '--batchsize', '256',
                        '--display-examples', 'False',
                        '--num-epochs', num_epochs,
                        '--log-every-n-secs', '-1',
                        '--log-every-n-epochs', '1',
                        '--raw_dataset_path', './build/paraphraser/',
                        '--learning_rate', '0.0001',
                        '--hidden_dim', '200',
                        '--validation-every-n-epochs', '5',
                        '--fasttext_embeddings_dict', './build/paraphraser/paraphraser.emb',
                        '--fasttext_model', './build/paraphraser/ft_0.8.3_nltk_yalen_sg_300.bin',
                        '--teacher-random-seed', '50',
                        '--bagging-folds-number', '5',
                        '--validation-patience', '3',
                        '--chosen-metrics', 'f1'
                        ])
    return metrics


@task
def train_ner(project):
    create_dir('ner')
    num_epochs = '1' if project.get_property('idle_train') == 'True' else '-1'
    metrics = bu.model(['-t', 'deeppavlov.tasks.ner.agents',
                        '-m', 'deeppavlov.agents.ner.ner:NERAgent',
                        '-mf', './build/ner',
                        '-dt', 'train:ordered',
                        '--dict-file', './build/ner/dict',
                        '--num-epochs', num_epochs,
                        '--learning_rate', '0.01',
                        '--batchsize', '2',
                        '--display-examples', 'False',
                        '--validation-every-n-epochs', '5',
                        '--log-every-n-epochs', '1',
                        '--log-every-n-secs', '-1',
                        '--chosen-metrics', 'f1'
                        ])
    return metrics


@task
def train_insults(project):
    create_dir('insults')
    num_epochs = '1' if project.get_property('idle_train') == 'True' else '1000'
    metrics = bu.model(['-t', 'deeppavlov.tasks.insults.agents',
                        '-m', 'deeppavlov.agents.insults.insults_agents:InsultsAgent',
                        '--model_file', './build/insults/cnn_word',
                        '-dt', 'train:ordered',
                        '--model_name', 'cnn_word',
                        '--log-every-n-secs', '60',
                        '--raw-dataset-path', './build/insults/',
                        '--batchsize', '64',
                        '--display-examples', 'False',
                        '--num-epochs', num_epochs,
                        '--max_sequence_length', '100',
                        '--learning_rate', '0.01',
                        '--learning_decay', '0.1',
                        '--filters_cnn', '256',
                        '--embedding_dim', '100',
                        '--kernel_sizes_cnn', '1 2 3',
                        '--regul_coef_conv', '0.001',
                        '--regul_coef_dense', '0.01',
                        '--dropout_rate', '0.5',
                        '--dense_dim', '100',
                        '--fasttext_model', './build/insults/reddit_fasttext_model.bin',
                        '--fasttext_embeddings_dict', './build/insults/emb_dict.emb',
                        '--bagging-folds-number', '3',
                        '-ve', '10',
                        '-vp', '5',
                        '--chosen-metric', 'auc'
                        ])
    return metrics


@task
def train_squad(project):
    create_dir('squad')
    if project.get_property('idle_train') == 'True':
        val_time = '600'
        time_limit = '900'
    else:
        val_time = '1800'
        time_limit = '86400'
    metrics = bu.model(['-t', 'squad',
                        '-m', 'deeppavlov.agents.squad.squad:SquadAgent',
                        '--batchsize', '64',
                        '--display-examples', 'False',
                        '--num-epochs', '-1',
                        '--max-train-time', time_limit,
                        '--log-every-n-secs', '60',
                        '--log-every-n-epochs', '-1',
                        '--validation-every-n-secs', val_time,
                        '--validation-every-n-epochs', '-1',
                        '--chosen-metrics', 'f1',
                        '--validation-patience', '5',
                        '--type', 'fastqa_default',
                        '--lr', '0.001',
                        '--lr_drop', '0.3',
                        '--linear_dropout', '0.25',
                        '--embedding_dropout', '0.5',
                        '--rnn_dropout', '0.25',
                        '--recurrent_dropout', '0.0',
                        '--input_dropout', '0.0',
                        '--output_dropout', '0.0',
                        '--context_enc_layers', '1',
                        '--question_enc_layers', '1',
                        '--encoder_hidden_dim', '300',
                        '--projection_dim', '300',
                        '--pointer_dim', '300',
                        '--model-file', './build/squad/squad1',
                        '--embedding_file', './build/squad/glove.840B.300d.txt'
                        ])
    return metrics


def compile_coreference(path):
    path = path + '/coref_kernels.so'
    if not os.path.isfile(path):
        print('Compiling the coref_kernels.cc')
        cmd = """#!/usr/bin/env bash

                # Build custom kernels.
                TF_INC=$(python3 -c 'import tensorflow as tf; print(tf.sysconfig.get_include())')

                # Linux (pip)
                g++ -std=c++11 -shared ./deeppavlov/agents/coreference/coref_kernels.cc -o {0} -I $TF_INC -fPIC -D_GLIBCXX_USE_CXX11_ABI=0

                # Linux (build from source)
                #g++ -std=c++11 -shared ./deeppavlov/agents/coreference/coref_kernels.cc -o {0} -I $TF_INC -fPIC

                # Mac
                #g++ -std=c++11 -shared ./deeppavlov/agents/coreference/coref_kernels.cc -o {0} -I $TF_INC -fPIC -D_GLIBCXX_USE_CXX11_ABI=0  -undefined dynamic_lookup"""
        cmd = cmd.format(path)
        os.system(cmd)
        print('End of compiling the coref_kernels.cc')


@task
def train_coreference(project):
    create_dir('coreference')
    mf = './build/coreference/'
    compile_coreference(mf)
    num_epochs = '20' if project.get_property('idle_train') == 'True' else '500'
    metrics = bu.model(['-t', 'deeppavlov.tasks.coreference.agents',
                        '-m', 'deeppavlov.agents.coreference.agents:CoreferenceAgent',
                        '-mf', mf,
                        '--language', 'russian',
                        '--name', 'test32',
                        '--pretrained_model', 'False',
                        '-dt', 'train:ordered',
                        '--batchsize', '1',
                        '--display-examples', 'False',
                        '--num-epochs', num_epochs,
                        '--validation-every-n-epochs', '5',
                        '--log-every-n-epochs', '1',
                        '--log-every-n-secs', '-1',
                        '--chosen-metric', 'conll-F-1',
                        '--validation-patience', '15',
                        '--train_on_gold', 'False',
                        '--random_seed', '5',
                        '--emb_format', 'bin',
                        '--embedding_size', '300'
                        ])
    return metrics


@task
def train_coref(project):
    create_dir('coref')
    num_epochs = '2' if project.get_property('idle_train') == 'True' else '20'
    metrics = bu.model(['-t', 'deeppavlov.tasks.coreference_scorer_model.agents:CoreferenceTeacher',
                        '-m', 'deeppavlov.agents.coreference_scorer_model.agents:CoreferenceAgent',
                        '--display-examples', 'False',
                        '--num-epochs', num_epochs,
                        '--log-every-n-secs', '-1',
                        '--log-every-n-epochs', '1',
                        '--validation-every-n-epochs', '1',
                        '--chosen-metrics', 'f1',
                        '--validation-patience', '5',
                        '--model-file', './build/coref',
                        '--embeddings_path', './build/coref/fasttext_embdgs.bin'
                        ])
    return metrics
