"""
Model training starts here. Configure the run in config.py, then run this
file to train your model on your dataset.
"""
from config import config

# Hack to use CPU (used if model can't fit into GPU memory)
# See https://github.com/fchollet/keras/issues/4613
if config['CPU_only']:
    import os
    os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
    os.environ["CUDA_VISIBLE_DEVICES"] = ""

from keras.callbacks import TensorBoard, ModelCheckpoint, EarlyStopping, CSVLogger
from keras.models import load_model
from models.base import get_model
from models.config import config as models_config
from datasets.base import get_generators
from datasets.config import config as datasets_config
import time
import os.path
import argparse


def train(model, generators, run_label):
    train_gen, val_gen = generators

    if not run_label:
        run_label = str(time.time())

    callbacks = []
    if config['tensorboard_callback']:
        callbacks.append(TensorBoard(log_dir=os.path.join('data', 'logs', run_label)))
    if config['early_stopper_callback']:
        callbacks.append(EarlyStopping(patience=config['patience']))
    if config['checkpointer_callback']:
        callbacks.append(
            ModelCheckpoint(
                filepath=os.path.join('data', 'checkpoints', run_label + '.hdf5'),
                verbose=config['verbose'],
                save_best_only=True
            )
        )

    model.fit_generator(
        generator=train_gen,
        steps_per_epoch=config['steps_per_epoch'],
        epochs=config['nb_epoch'],
        verbose=config['verbose'],
        callbacks=callbacks,
        validation_data=val_gen,
        validation_steps=config['validation_steps'],
        workers=config['workers'])

    return model


def main(model_name, dataset, model_path=None):
    """Given a model and a training set, train."""
    paths = models_config['models'][model_name]['paths']
    input_shapes = [x['input_shape'] for x in paths]
    preprocessing_steps = [x['preprocessing'] for x in paths]
    if config['class_limit']:
        nb_classes = config['class_limit']
    else:
        nb_classes = datasets_config['datasets'][dataset]['nb_classes']

    # Get the model.
    if model_path:
        model = load_model(model_path)
    else: 
        model = get_model(nb_classes, model_name, config['sequence_length'],
                          config['optimizer'], config['learning_rate'], input_shapes,
                          config['verbose'])

    # Get the data generators.
    generators = get_generators(dataset, config['sequence_length'], nb_classes,
                                input_shapes, preprocessing_steps,
                                config['batch_size'])
    
    train(model, generators, config['run_label'])
        
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Train video classifiers.')
    parser.add_argument('model_name', action='store',
                        help='The model to be trained',
                        choices=list(models_config['models'].keys()))
    parser.add_argument('dataset', action='store',
                        help='The dataset to train on',
                        choices=list(datasets_config['datasets'].keys()))
    parser.add_argument('--model_path', action='store', dest='model_path',
                        help='Saved model to load.', default=None)
    args = parser.parse_args()

    main(args.model_name, args.dataset, args.model_path)
