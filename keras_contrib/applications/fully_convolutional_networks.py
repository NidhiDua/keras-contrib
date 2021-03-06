""" Fully Convolutional Networks

Based on the paper:

   - [Fully Convolutional Networks for Semantic Segmentation](https://arxiv.org/abs/1605.06211)

Implementation adapted from [Keras-FCN](https://github.com/aurora95/Keras-FCN).

"""
import numpy as np
import matplotlib.pyplot as plt
import os
import sys
from keras import backend as K
from keras_contrib.applications import densenet
from keras.models import Model
from keras.regularizers import l2
from keras.layers import Conv2D
from keras.layers import BatchNormalization
from keras.layers import Activation
from keras.layers import MaxPooling2D
from keras.layers import Add
from keras.engine import Layer
from keras_applications.imagenet_utils import _obtain_input_shape
import keras.backend as K
import tensorflow as tf


def conv_relu(nb_filter, nb_row, nb_col, subsample=(1, 1), border_mode='same', bias=True, w_decay=0.01):
    def f(x):
        with K.name_scope('conv_relu'):
            x = Conv2D(filters=nb_filter, kernel_size=(nb_row, nb_col), stride=subsample, use_bias=bias,
                       kernel_initializer="he_normal", W_regularizer=l2(w_decay), border_mode=border_mode)(x)
            x = Activation("relu")(x)
        return x
    return f


def conv_bn(nb_filter, nb_row, nb_col, subsample=(1, 1), border_mode='same', bias=True, w_decay=0.01):
    def f(x):
        with K.name_scope('conv_bn'):
            x = Conv2D(filters=nb_filter, kernel_size=(nb_row, nb_col), stride=subsample, use_bias=bias,
                       kernel_initializer="he_normal", W_regularizer=l2(w_decay), border_mode=border_mode)(x)
            x = BatchNormalization(mode=0, axis=-1)(x)
        return x
    return f


def conv_bn_relu(nb_filter, nb_row, nb_col, subsample=(1, 1), border_mode='same', bias=True, w_decay=0.01):
    def f(x):
        with K.name_scope('conv_bn_relu'):
            x = Conv2D(filters=nb_filter, kernel_size=(nb_row, nb_col), stride=subsample, use_bias=bias,
                       kernel_initializer="he_normal", W_regularizer=l2(w_decay), border_mode=border_mode)(x)
            x = BatchNormalization(mode=0, axis=-1)(x)
            x = Activation("relu")(x)
        return x
    return f


def bn_relu_conv(nb_filter, nb_row, nb_col, subsample=(1, 1), border_mode='same', bias=True, w_decay=0.01):
    def f(x):
        with K.name_scope('bn_relu_conv'):
            x = BatchNormalization(mode=0, axis=-1)(x)
            x = Activation("relu")(x)
            x = Conv2D(filters=nb_filter, kernel_size=(nb_row, nb_col), stride=subsample, use_bias=bias,
                       kernel_initializer="he_normal", W_regularizer=l2(w_decay), border_mode=border_mode)(x)
        return x
    return f


def atrous_conv_bn(nb_filter, nb_row, nb_col, atrous_rate=(2, 2), subsample=(1, 1), border_mode='same', bias=True, w_decay=0.01):
    def f(x):
        with K.name_scope('atrous_conv_bn'):
            x = Conv2D(filters=nb_filter, kernel_size=(nb_row, nb_col), dilation_rate=atrous_rate, stride=subsample, use_bias=bias,
                       kernel_initializer="he_normal", kernel_regularizer=l2(w_decay), padding=border_mode)(x)
            x = BatchNormalization(mode=0, axis=-1)(x)
        return x
    return f


def atrous_conv_bn_relu(nb_filter, nb_row, nb_col, atrous_rate=(2, 2), subsample=(1, 1), border_mode='same', bias=True, w_decay=0.01):
    def f(x):
        with K.name_scope('atrous_conv_bn_relu'):
            x = Conv2D(filters=nb_filter, kernel_size=(nb_row, nb_col), dilation_rate=atrous_rate, stride=subsample, use_bias=bias,
                       kernel_initializer="he_normal", kernel_regularizer=l2(w_decay), padding=border_mode)(x)
            x = BatchNormalization(mode=0, axis=-1)(x)
            x = Activation("relu")(x)
        return x
    return f


def get_weights_path_vgg16():
    TF_WEIGHTS_PATH = 'https://github.com/fchollet/deep-learning-models/releases/download/v0.1/vgg16_weights_tf_dim_ordering_tf_kernels.h5'
    weights_path = get_file(
        'vgg16_weights_tf_dim_ordering_tf_kernels.h5', TF_WEIGHTS_PATH, cache_subdir='models')
    return weights_path


def get_weights_path_resnet():
    TF_WEIGHTS_PATH = 'https://github.com/fchollet/deep-learning-models/releases/download/v0.2/resnet50_weights_tf_dim_ordering_tf_kernels.h5'
    weights_path = get_file(
        'resnet50_weights_tf_dim_ordering_tf_kernels.h5', TF_WEIGHTS_PATH, cache_subdir='models')


def resize_images_bilinear(X, height_factor=1, width_factor=1, target_height=None, target_width=None, data_format='default'):
    '''Resizes the images contained in a 4D tensor of shape
    - [batch, channels, height, width] (for 'channels_first' data_format)
    - [batch, height, width, channels] (for 'channels_last' data_format)
    by a factor of (height_factor, width_factor). Both factors should be
    positive integers.
    '''
    if data_format == 'default':
        data_format = K.image_data_format()
    if data_format == 'channels_first':
        original_shape = K.int_shape(X)
        if target_height and target_width:
            new_shape = tf.constant(
                np.array((target_height, target_width)).astype('int32'))
        else:
            new_shape = tf.shape(X)[2:]
            new_shape *= tf.constant(
                np.array([height_factor, width_factor]).astype('int32'))
        X = K.permute_dimensions(X, [0, 2, 3, 1])
        X = tf.image.resize_bilinear(X, new_shape)
        X = K.permute_dimensions(X, [0, 3, 1, 2])
        if target_height and target_width:
            X.set_shape((None, None, target_height, target_width))
        else:
            X.set_shape(
                (None, None, original_shape[2] * height_factor, original_shape[3] * width_factor))
        return X
    elif data_format == 'channels_last':
        original_shape = K.int_shape(X)
        if target_height and target_width:
            new_shape = tf.constant(
                np.array((target_height, target_width)).astype('int32'))
        else:
            new_shape = tf.shape(X)[1:3]
            new_shape *= tf.constant(
                np.array([height_factor, width_factor]).astype('int32'))
        X = tf.image.resize_bilinear(X, new_shape)
        if target_height and target_width:
            X.set_shape((None, target_height, target_width, None))
        else:
            X.set_shape(
                (None, original_shape[1] * height_factor, original_shape[2] * width_factor, None))
        return X
    else:
        raise Exception('Invalid data_format: ' + data_format)


class BilinearUpSampling2D(Layer):
    """ Bilinear Upsampling

    TODO: remove and replace with UpSampling2D when https://github.com/keras-team/keras/pull/9303 is available
    """

    def __init__(self, size=(1, 1), target_size=None, data_format='default', **kwargs):
        if data_format == 'default':
            data_format = K.image_data_format()
        self.size = tuple(size)
        if target_size is not None:
            self.target_size = tuple(target_size)
        else:
            self.target_size = None
        assert data_format in {
            'channels_last', 'channels_first'}, 'data_format must be in {tf, th}'
        self.data_format = data_format
        self.input_spec = [InputSpec(ndim=4)]
        super(BilinearUpSampling2D, self).__init__(**kwargs)

    def compute_output_shape(self, input_shape):
        if self.data_format == 'channels_first':
            width = int(self.size[0] * input_shape[2]
                        if input_shape[2] is not None else None)
            height = int(self.size[1] * input_shape[3]
                         if input_shape[3] is not None else None)
            if self.target_size is not None:
                width = self.target_size[0]
                height = self.target_size[1]
            return (input_shape[0],
                    input_shape[1],
                    width,
                    height)
        elif self.data_format == 'channels_last':
            width = int(self.size[0] * input_shape[1]
                        if input_shape[1] is not None else None)
            height = int(self.size[1] * input_shape[2]
                         if input_shape[2] is not None else None)
            if self.target_size is not None:
                width = self.target_size[0]
                height = self.target_size[1]
            return (input_shape[0],
                    width,
                    height,
                    input_shape[3])
        else:
            raise Exception('Invalid data_format: ' + self.data_format)

    def call(self, x, mask=None):
        if self.target_size is not None:
            return resize_images_bilinear(x, target_height=self.target_size[0], target_width=self.target_size[1], data_format=self.data_format)
        else:
            return resize_images_bilinear(x, height_factor=self.size[0], width_factor=self.size[1], data_format=self.data_format)

    def get_config(self):
        config = {'size': self.size, 'target_size': self.target_size}
        base_config = super(BilinearUpSampling2D, self).get_config()
        return dict(list(base_config.items()) + list(config.items()))


# The original help functions from keras does not have weight regularizers, so I modified them.
# Also, I changed these two functions into functional style
def identity_block(kernel_size, filters, stage, block, weight_decay=0., batch_momentum=0.99):
    '''The identity_block is the block that has no conv layer at shortcut
    # Arguments
        kernel_size: defualt 3, the kernel size of middle conv layer at main path
        filters: list of integers, the nb_filters of 3 conv layer at main path
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names
    '''
    def f(input_tensor):
        nb_filter1, nb_filter2, nb_filter3 = filters
        if K.image_data_format() == 'channels_last':
            bn_axis = 3
        else:
            bn_axis = 1
        conv_name_base = 'res' + str(stage) + block + '_branch'
        bn_name_base = 'bn' + str(stage) + block + '_branch'

        x = Conv2D(nb_filter1, (1, 1), name=conv_name_base + '2a',
                   kernel_regularizer=l2(weight_decay))(input_tensor)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2a', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter2, (kernel_size, kernel_size),
                   padding='same', name=conv_name_base + '2b', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2b', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter3, (1, 1), name=conv_name_base +
                   '2c', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2c', momentum=batch_momentum)(x)

        x = Add()([x, input_tensor])
        x = Activation('relu')(x)
        return x
    return f


def conv_block(kernel_size, filters, stage, block, weight_decay=0., strides=(2, 2), batch_momentum=0.99):
    '''conv_block is the block that has a conv layer at shortcut
    # Arguments
        kernel_size: defualt 3, the kernel size of middle conv layer at main path
        filters: list of integers, the nb_filters of 3 conv layer at main path
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names
    Note that from stage 3, the first conv layer at main path is with strides=(2,2)
    And the shortcut should have strides=(2,2) as well
    '''
    def f(input_tensor):
        nb_filter1, nb_filter2, nb_filter3 = filters
        if K.image_data_format() == 'channels_last':
            bn_axis = 3
        else:
            bn_axis = 1
        conv_name_base = 'res' + str(stage) + block + '_branch'
        bn_name_base = 'bn' + str(stage) + block + '_branch'

        x = Conv2D(nb_filter1, (1, 1), strides=strides,
                   name=conv_name_base + '2a', kernel_regularizer=l2(weight_decay))(input_tensor)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2a', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter2, (kernel_size, kernel_size), padding='same',
                   name=conv_name_base + '2b', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2b', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter3, (1, 1), name=conv_name_base +
                   '2c', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2c', momentum=batch_momentum)(x)

        shortcut = Conv2D(nb_filter3, (1, 1), strides=strides,
                          name=conv_name_base + '1', kernel_regularizer=l2(weight_decay))(input_tensor)
        shortcut = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '1', momentum=batch_momentum)(shortcut)

        x = Add()([x, shortcut])
        x = Activation('relu')(x)
        return x
    return f


# Atrous-Convolution version of residual blocks
def atrous_identity_block(kernel_size, filters, stage, block, weight_decay=0., atrous_rate=(2, 2), batch_momentum=0.99):
    '''The identity_block is the block that has no conv layer at shortcut
    # Arguments
        kernel_size: defualt 3, the kernel size of middle conv layer at main path
        filters: list of integers, the nb_filters of 3 conv layer at main path
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names
    '''
    def f(input_tensor):
        nb_filter1, nb_filter2, nb_filter3 = filters
        if K.image_data_format() == 'channels_last':
            bn_axis = 3
        else:
            bn_axis = 1
        conv_name_base = 'res' + str(stage) + block + '_branch'
        bn_name_base = 'bn' + str(stage) + block + '_branch'

        x = Conv2D(nb_filter1, (1, 1), name=conv_name_base + '2a',
                   kernel_regularizer=l2(weight_decay))(input_tensor)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2a', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter2, (kernel_size, kernel_size), dilation_rate=atrous_rate,
                   padding='same', name=conv_name_base + '2b', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2b', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter3, (1, 1), name=conv_name_base +
                   '2c', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2c', momentum=batch_momentum)(x)

        x = Add()([x, input_tensor])
        x = Activation('relu')(x)
        return x
    return f


def atrous_conv_block(kernel_size, filters, stage, block, weight_decay=0., strides=(1, 1), atrous_rate=(2, 2), batch_momentum=0.99):
    '''conv_block is the block that has a conv layer at shortcut
    # Arguments
        kernel_size: defualt 3, the kernel size of middle conv layer at main path
        filters: list of integers, the nb_filters of 3 conv layer at main path
        stage: integer, current stage label, used for generating layer names
        block: 'a','b'..., current block label, used for generating layer names
    '''
    def f(input_tensor):
        nb_filter1, nb_filter2, nb_filter3 = filters
        if K.image_data_format() == 'channels_last':
            bn_axis = 3
        else:
            bn_axis = 1
        conv_name_base = 'res' + str(stage) + block + '_branch'
        bn_name_base = 'bn' + str(stage) + block + '_branch'

        x = Conv2D(nb_filter1, (1, 1), strides=strides,
                   name=conv_name_base + '2a', kernel_regularizer=l2(weight_decay))(input_tensor)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2a', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter2, (kernel_size, kernel_size), padding='same', dilation_rate=atrous_rate,
                   name=conv_name_base + '2b', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2b', momentum=batch_momentum)(x)
        x = Activation('relu')(x)

        x = Conv2D(nb_filter3, (1, 1), name=conv_name_base +
                   '2c', kernel_regularizer=l2(weight_decay))(x)
        x = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '2c', momentum=batch_momentum)(x)

        shortcut = Conv2D(nb_filter3, (1, 1), strides=strides,
                          name=conv_name_base + '1', kernel_regularizer=l2(weight_decay))(input_tensor)
        shortcut = BatchNormalization(
            axis=bn_axis, name=bn_name_base + '1', momentum=batch_momentum)(shortcut)

        x = Add()([x, shortcut])
        x = Activation('relu')(x)
        return x
    return f


def top(x, input_shape, classes, activation, weight_decay):

    x = Conv2D(classes, (1, 1), activation='linear',
               padding='same', kernel_regularizer=l2(weight_decay),
               use_bias=False)(x)

    if K.image_data_format() == 'channels_first':
        channel, row, col = input_shape
    else:
        row, col, channel = input_shape

    # TODO(ahundt) this is modified for the sigmoid case! also use loss_shape
    if activation is 'sigmoid':
        x = Reshape((row * col * classes,))(x)

    return x


def FCN_Vgg16_32s(input_shape=None, weight_decay=0., batch_momentum=0.9, batch_shape=None, classes=21):
    if batch_shape:
        img_input = Input(batch_shape=batch_shape)
        image_size = batch_shape[1:3]
    else:
        img_input = Input(shape=input_shape)
        image_size = input_shape[0:2]
    # Block 1
    x = Conv2D(64, (3, 3), activation='relu', padding='same',
               name='block1_conv1', kernel_regularizer=l2(weight_decay))(img_input)
    x = Conv2D(64, (3, 3), activation='relu', padding='same',
               name='block1_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block1_pool')(x)

    # Block 2
    x = Conv2D(128, (3, 3), activation='relu', padding='same',
               name='block2_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(128, (3, 3), activation='relu', padding='same',
               name='block2_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block2_pool')(x)

    # Block 3
    x = Conv2D(256, (3, 3), activation='relu', padding='same',
               name='block3_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(256, (3, 3), activation='relu', padding='same',
               name='block3_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(256, (3, 3), activation='relu', padding='same',
               name='block3_conv3', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block3_pool')(x)

    # Block 4
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name='block4_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name='block4_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name='block4_conv3', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block4_pool')(x)

    # Block 5
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name='block5_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name='block5_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name='block5_conv3', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block5_pool')(x)

    # Convolutional layers transfered from fully-connected layers
    x = Conv2D(4096, (7, 7), activation='relu', padding='same',
               name='fc1', kernel_regularizer=l2(weight_decay))(x)
    x = Dropout(0.5)(x)
    x = Conv2D(4096, (1, 1), activation='relu', padding='same',
               name='fc2', kernel_regularizer=l2(weight_decay))(x)
    x = Dropout(0.5)(x)
    # classifying layer
    x = Conv2D(classes, (1, 1), kernel_initializer='he_normal', activation='linear',
               padding='valid', strides=(1, 1), kernel_regularizer=l2(weight_decay))(x)

    x = BilinearUpSampling2D(size=(32, 32))(x)

    model = Model(img_input, x)

    weights_path = os.path.expanduser(os.path.join(
        '~', '.keras/models/fcn_vgg16_weights_tf_dim_ordering_tf_kernels.h5'))
    model.load_weights(weights_path, by_name=True)
    return model


def AtrousFCN_Vgg16_16s(input_shape=None, weight_decay=0., batch_momentum=0.9, batch_shape=None,
                        classes=21, weights_path=None, upsample=True, input_tensor=None, include_top=False,
                        dilation_rate=(2, 2), name=''):
    if batch_shape:
        img_input = Input(tensor=input_tensor, batch_shape=batch_shape)
        if upsample:
            image_size = batch_shape[1:3]
    else:
        img_input = Input(tensor=input_tensor, shape=input_shape)
        if upsample:
            image_size = input_shape[0:2]
    # Block 1
    x = Conv2D(64, (3, 3), activation='relu', padding='same',
               name=name + 'block1_conv1', kernel_regularizer=l2(weight_decay))(img_input)
    x = Conv2D(64, (3, 3), activation='relu', padding='same',
               name=name + 'block1_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block1_pool')(x)

    # Block 2
    x = Conv2D(128, (3, 3), activation='relu', padding='same',
               name=name + 'block2_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(128, (3, 3), activation='relu', padding='same',
               name=name + 'block2_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block2_pool')(x)

    # Block 3
    x = Conv2D(256, (3, 3), activation='relu', padding='same',
               name=name + 'block3_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(256, (3, 3), activation='relu', padding='same',
               name=name + 'block3_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(256, (3, 3), activation='relu', padding='same',
               name=name + 'block3_conv3', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block3_pool')(x)

    # Block 4
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name=name + 'block4_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name=name + 'block4_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name=name + 'block4_conv3', kernel_regularizer=l2(weight_decay))(x)
    x = MaxPooling2D((2, 2), strides=(2, 2), name='block4_pool')(x)

    # Block 5
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name=name + 'block5_conv1', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name=name + 'block5_conv2', kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(512, (3, 3), activation='relu', padding='same',
               name=name + 'block5_conv3', kernel_regularizer=l2(weight_decay))(x)
    if dilation_rate == 1 or dilation_rate == (1, 1):
        x = MaxPooling2D((2, 2), strides=(2, 2), name='block4_pool')(x)

    if include_top:
        # Convolutional layers transfered from fully-connected layers
        x = Conv2D(4096, (7, 7), activation='relu', padding='same', dilation_rate=dilation_rate,
                   name='fc1', kernel_regularizer=l2(weight_decay))(x)
        x = Dropout(0.5)(x)
        x = Conv2D(4096, (1, 1), activation='relu', padding='same',
                   name='fc2', kernel_regularizer=l2(weight_decay))(x)
        x = Dropout(0.5)(x)
        # classifying layer
        x = Conv2D(classes, (1, 1), kernel_initializer='he_normal', activation='linear',
                   padding='valid', strides=(1, 1), kernel_regularizer=l2(weight_decay))(x)

    if upsample:
        x = BilinearUpSampling2D(target_size=tuple(image_size))(x)

    model = Model(img_input, x)

    if weights_path is None:
        weights_path = os.path.expanduser(os.path.join(
            '~', '.keras/models/vgg16_weights_tf_dim_ordering_tf_kernels_notop.h5'))
        if not os.path.exists(weights_path):
            temp_weights_path = os.path.expanduser(os.path.join(
                '~', '.keras/models/fcn_vgg16_weights_tf_dim_ordering_tf_kernels.h5'))
            if not os.path.exists(temp_weights_path):
                # download the model if we don't have it yet
                temp_model = keras.applications.vgg16.VGG16(include_top=False)
                temp_model.save_weights(weights_path)
                del(temp_model)
            model.load_weights(weights_path, by_name=True, reshape=True)
            model.save_weights(weights_path)
        else:
            model.load_weights(weights_path)
    else:
        model.load_weights(weights_path)

    return model


def FCN_Resnet50_32s(input_shape=None, weight_decay=0., batch_momentum=0.9, batch_shape=None, classes=21):
    if batch_shape:
        img_input = Input(batch_shape=batch_shape)
        image_size = batch_shape[1:3]
    else:
        img_input = Input(shape=input_shape)
        image_size = input_shape[0:2]

    bn_axis = 3

    x = Conv2D(64, (7, 7), strides=(2, 2), padding='same',
               name='conv1', kernel_regularizer=l2(weight_decay))(img_input)
    x = BatchNormalization(axis=bn_axis, name='bn_conv1')(x)
    x = Activation('relu')(x)
    x = MaxPooling2D((3, 3), strides=(2, 2))(x)

    x = conv_block(3, [64, 64, 256], stage=2, block='a', strides=(1, 1))(x)
    x = identity_block(3, [64, 64, 256], stage=2, block='b')(x)
    x = identity_block(3, [64, 64, 256], stage=2, block='c')(x)

    x = conv_block(3, [128, 128, 512], stage=3, block='a')(x)
    x = identity_block(3, [128, 128, 512], stage=3, block='b')(x)
    x = identity_block(3, [128, 128, 512], stage=3, block='c')(x)
    x = identity_block(3, [128, 128, 512], stage=3, block='d')(x)

    x = conv_block(3, [256, 256, 1024], stage=4, block='a')(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='b')(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='c')(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='d')(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='e')(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='f')(x)

    x = conv_block(3, [512, 512, 2048], stage=5, block='a')(x)
    x = identity_block(3, [512, 512, 2048], stage=5, block='b')(x)
    x = identity_block(3, [512, 512, 2048], stage=5, block='c')(x)
    # classifying layer
    x = Conv2D(classes, (1, 1), kernel_initializer='he_normal', activation='linear',
               padding='valid', strides=(1, 1), kernel_regularizer=l2(weight_decay))(x)

    x = BilinearUpSampling2D(size=(32, 32))(x)

    model = Model(img_input, x)
    weights_path = os.path.expanduser(os.path.join(
        '~', '.keras/models/fcn_resnet50_weights_tf_dim_ordering_tf_kernels.h5'))
    model.load_weights(weights_path, by_name=True)
    return model


def AtrousFCN_Resnet50_16s(input_shape=None, weight_decay=0., batch_momentum=0.9, batch_shape=None, classes=21,
                           include_top=False, upsample=False):
    if input_shape is None and input_tensor is not None:
        batch_shape = keras.backend.int_shape(input_tensor)

    if batch_shape:
        img_input = Input(batch_shape=batch_shape)
        image_size = batch_shape[1:3]
    elif input_shape is not None:
        img_input = Input(shape=input_shape)
        image_size = input_shape[0:2]

    bn_axis = 3

    x = Conv2D(64, (7, 7), strides=(2, 2), padding='same',
               name='conv1', kernel_regularizer=l2(weight_decay))(img_input)
    x = BatchNormalization(axis=bn_axis, name='bn_conv1',
                           momentum=batch_momentum)(x)
    x = Activation('relu')(x)
    x = MaxPooling2D((3, 3), strides=(2, 2))(x)

    x = conv_block(3, [64, 64, 256], stage=2, block='a', weight_decay=weight_decay, strides=(
        1, 1), batch_momentum=batch_momentum)(x)
    x = identity_block(3, [64, 64, 256], stage=2, block='b',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [64, 64, 256], stage=2, block='c',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)

    x = conv_block(3, [128, 128, 512], stage=3, block='a',
                   weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [128, 128, 512], stage=3, block='b',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [128, 128, 512], stage=3, block='c',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [128, 128, 512], stage=3, block='d',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)

    x = conv_block(3, [256, 256, 1024], stage=4, block='a',
                   weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='b',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='c',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='d',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='e',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)
    x = identity_block(3, [256, 256, 1024], stage=4, block='f',
                       weight_decay=weight_decay, batch_momentum=batch_momentum)(x)

    x = atrous_conv_block(3, [512, 512, 2048], stage=5, block='a', weight_decay=weight_decay, atrous_rate=(
        2, 2), batch_momentum=batch_momentum)(x)
    x = atrous_identity_block(3, [512, 512, 2048], stage=5, block='b', weight_decay=weight_decay, atrous_rate=(
        2, 2), batch_momentum=batch_momentum)(x)
    x = atrous_identity_block(3, [512, 512, 2048], stage=5, block='c', weight_decay=weight_decay, atrous_rate=(
        2, 2), batch_momentum=batch_momentum)(x)
    # classifying layer
    #  x = Conv2D(classes, (3, 3), dilation_rate=(2, 2), kernel_initializer='normal', activation='linear', padding='same', strides=(1, 1), kernel_regularizer=l2(weight_decay))(x)
    x = Conv2D(classes, (1, 1), kernel_initializer='he_normal', activation='linear',
               padding='same', strides=(1, 1), kernel_regularizer=l2(weight_decay))(x)

    if upsample:
        x = BilinearUpSampling2D(target_size=tuple(image_size))(x)

    model = Model(img_input, x)

    if weights_path is None:
        weights_path = os.path.expanduser(os.path.join(
            '~', '.keras/models/resnet50_weights_tf_dim_ordering_tf_kernels_notop.h5'))
        if not os.path.exists(weights_path):
            temp_weights_path = os.path.expanduser(os.path.join(
                '~', '.keras/models/fcn_resnet50_weights_tf_dim_ordering_tf_kernels.h5'))
            if not os.path.exists(temp_weights_path):
                # download the model if we don't have it yet
                temp_model = keras.applications.resnet50.ResNet50(include_top=False)
                temp_model.save_weights(weights_path)
                del(temp_model)
            model.load_weights(weights_path, by_name=True, reshape=True)
            model.save_weights(weights_path)
        else:
            model.load_weights(weights_path)
    else:
        model.load_weights(weights_path)
    return model


def Atrous_DenseNet(input_shape=None, weight_decay=1E-4,
                    batch_momentum=0.9, batch_shape=None, classes=21,
                    include_top=False, activation='sigmoid'):
    # TODO(ahundt) pass the parameters but use defaults for now
    if include_top is True:
        # TODO(ahundt) Softmax is pre-applied, so need different train, inference, evaluate.
        # TODO(ahundt) for multi-label try per class sigmoid top as follows:
        # x = Reshape((row * col * classes))(x)
        # x = Activation('sigmoid')(x)
        # x = Reshape((row, col, classes))(x)
        return densenet.DenseNet(depth=None, nb_dense_block=3, growth_rate=32,
                                 nb_filter=-1, nb_layers_per_block=[6, 12, 24, 16],
                                 bottleneck=True, reduction=0.5, dropout_rate=0.2,
                                 weight_decay=1E-4,
                                 include_top=True, top='segmentation',
                                 weights=None, input_tensor=None,
                                 input_shape=input_shape,
                                 classes=classes, transition_dilation_rate=2,
                                 transition_kernel_size=(1, 1),
                                 transition_pooling=None)

    # if batch_shape:
    #     img_input = Input(batch_shape=batch_shape)
    #     image_size = batch_shape[1:3]
    # else:
    #     img_input = Input(shape=input_shape)
    #     image_size = input_shape[0:2]

    input_shape = _obtain_input_shape(input_shape,
                                      default_size=32,
                                      min_size=16,
                                      data_format=K.image_data_format(),
                                      include_top=False)
    img_input = Input(shape=input_shape)

    x = densenet.__create_dense_net(classes, img_input,
                                    depth=None, nb_dense_block=3, growth_rate=32,
                                    nb_filter=-1, nb_layers_per_block=[6, 12, 24, 16],
                                    bottleneck=True, reduction=0.5, dropout_rate=0.2,
                                    weight_decay=1E-4, top='segmentation',
                                    input_shape=input_shape,
                                    transition_dilation_rate=2,
                                    transition_kernel_size=(1, 1),
                                    transition_pooling=None,
                                    include_top=include_top)

    x = top(x, input_shape, classes, activation, weight_decay)

    model = Model(img_input, x, name='Atrous_DenseNet')
    # TODO(ahundt) add weight loading
    return model


def DenseNet_FCN(input_shape=None, weight_decay=1E-4,
                 batch_momentum=0.9, batch_shape=None, classes=21,
                 include_top=False, activation='sigmoid'):
    if include_top is True:
        # TODO(ahundt) Softmax is pre-applied, so need different train, inference, evaluate.
        # TODO(ahundt) for multi-label try per class sigmoid top as follows:
        # x = Reshape((row * col * classes))(x)
        # x = Activation('sigmoid')(x)
        # x = Reshape((row, col, classes))(x)
        return densenet.DenseNetFCN(input_shape=input_shape,
                                    weights=None, classes=classes,
                                    nb_layers_per_block=[4, 5, 7, 10, 12, 15],
                                    growth_rate=16,
                                    dropout_rate=0.2)

    # if batch_shape:
    #     img_input = Input(batch_shape=batch_shape)
    #     image_size = batch_shape[1:3]
    # else:
    #     img_input = Input(shape=input_shape)
    #     image_size = input_shape[0:2]

    input_shape = _obtain_input_shape(input_shape,
                                      default_size=32,
                                      min_size=16,
                                      data_format=K.image_data_format(),
                                      include_top=False)
    img_input = Input(shape=input_shape)

    x = densenet.__create_fcn_dense_net(classes, img_input,
                                        input_shape=input_shape,
                                        nb_layers_per_block=[
                                            4, 5, 7, 10, 12, 15],
                                        growth_rate=16,
                                        dropout_rate=0.2,
                                        include_top=include_top)

    x = top(x, input_shape, classes, activation, weight_decay)
    # TODO(ahundt) add weight loading
    model = Model(img_input, x, name='DenseNet_FCN')
    return model
