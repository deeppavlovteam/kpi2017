"""
Copyright 2017 Neural Networks and Deep Learning lab, MIPT

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import parlai.core.build_data as build_data
import os
from os.path import join
import time
from . import utils

def build(opt):
    # get path to data directory and create folders tree
    dpath = join(opt['datapath'], 'coreference')  # opt['datapath'] = './built/'
    # define version if any, and languages
    version = '1.0'
    language = opt['language']
    dpath = join(dpath, language)

    # check if data had been previously built
    if not build_data.built(dpath, version_string=version):
        print('[building data: ' + dpath + '] ...')

        # make a clean directory if needed
        if build_data.built(dpath):
            # an older version exists, so remove these outdated files.
            build_data.remove_dir(dpath)

        # Build the folders tree
        build_data.make_dir(dpath)
        build_data.make_dir(join(dpath, 'embeddings'))
        build_data.make_dir(join(dpath, 'logs'))
        build_data.make_dir(join(dpath, 'report', 'response_files'))
        build_data.make_dir(join(dpath, 'report', 'results'))
        build_data.make_dir(join(dpath, 'pure_text'))
        build_data.make_dir(join(dpath, 'scorer'))
        build_data.make_dir(join(dpath, 'vocab'))
        build_data.make_dir(join(dpath, 'train'))
        build_data.make_dir(join(dpath, 'test'))
        build_data.make_dir(join(dpath, 'valid'))

        # urls
        dataset_url = 'http://rucoref.maimbava.net/files/rucoref_29.10.2015.zip'
        embed_url = 'https://drive.google.com/open?id=0B7A8-2DSIVoeelVIT1BMUFVLSnM'
        scorer_url = 'http://conll.cemantix.org/download/reference-coreference-scorers.v8.01.tar.gz'
        
        # download embeddings
        start = time.time()
        print('[Download the word embeddings]...')
        build_data.download(embed_url, join(dpath, 'embeddings'), 'embeddings_lenta.vec')
        print('[End of download the word embeddings]...')
        
        # download the conll-2012 scorer v 8.1
        print('[Download the conll-2012 scorer]...')
        build_data.download(scorer_url, join(dpath, 'scorer'), 'reference-coreference-scorers.v8.01.tar.gz')
        build_data.untar(join(dpath, 'scorer'), 'reference-coreference-scorers.v8.01.tar.gz')
        print('[Scorer was dawnloads]...')      
        
        # download dataset
        fname = 'rucoref_29.10.2015.zip'
        print('[Download the rucoref dataset]...')
        build_data.make_dir(join(dpath, 'rucoref_29.10.2015'))
        build_data.download(dataset_url, join(dpath, 'rucoref_29.10.2015'), fname)
        # uncompress it
        build_data.untar(join(dpath, 'rucoref_29.10.2015'), 'rucoref_29.10.2015.zip')
        print('End of download: time - {}'.format(time.time()-start))
        
        # Get pure text from Tokens.txt for creating char dictionary
        utils.get_all_texts_from_tokens_file(join(dpath, 'rucoref_29.10.2015', 'Tokens.txt'), join(dpath, 'pure_text', 'Pure_text.txt'))
        
        # Get char dictionary from pure text
        utils.get_char_vocab(join(dpath, 'pure_text', 'Pure_text.txt'), join(dpath, 'vocab', 'char_vocab.{}.txt'.format(language)))
        
        # Convertation rucorpus files in conll files
        conllpath = join(dpath, 'ru_conll')
        build_data.make_dir(conllpath)
        utils.RuCoref2CoNLL(join(dpath, 'rucoref_29.10.2015'), conllpath, language)

        # splits conll files
        start = time.time()
        conlls = join(dpath, 'ru_conlls')
        build_data.make_dir(conlls)
        utils.split_doc(join(conllpath, language + '.v4_conll'), conlls, language)
        build_data.remove_dir(conllpath)

        # create train valid test partitions
        # train_test_split(conlls,dpath,opt['split'],opt['random-seed'])
        utils.train_test_split(conlls, join(dpath, 'test'), 0.2, None)
        utils.train_test_split(join(dpath, 'test'), join(dpath, 'train'), 0.3, None)
        z = os.listdir(conlls)
        for x in z:
            build_data.move(join(conlls, x), join(dpath, 'valid', x))

        build_data.remove_dir(conlls)
        build_data.remove_dir(join(dpath, 'rucoref_29.10.2015'))
        print('End of data splitting. Time - {}'.format(time.time()-start))
        
        cmd = """#  Build custom kernels.
                    TF_INC=$(python -c 'import tensorflow as tf; print(tf.sysconfig.get_include())')

                    # Linux (pip)
                    #g++ -std=c++11 -shared coref_kernels.cc -o coref_kernels.so -I $TF_INC -fPIC -D_GLIBCXX_USE_CXX11_ABI=0

                    # Linux (build from source)
                    g++ -std=c++11 -shared coref_kernels.cc -o coref_kernels.so -I $TF_INC -fPIC

                    # Mac
                    #g++ -std=c++11 -shared coref_kernels.cc -o coref_kernels.so -I $TF_INC -fPIC -D_GLIBCXX_USE_CXX11_ABI=0  -undefined dynamic_lookup"""
        os.system(cmd)

        # mark the data as built
        build_data.mark_done(dpath, version_string=version)
        print('[Datasets done.]')
        return None
