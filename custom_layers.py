#! /usr/bin/env python
#
# Drop connect taken from:
# https://github.com/andry9454/KerasDropconnect
#
# Temporal max pooling taken from :
# https://gist.github.com/nigeljyng/881ae30e7c35ca2b77f6975e50736493

import numpy as np

import tensorflow as tf

from keras import backend as K
from keras.layers.wrappers import Wrapper
from keras.engine import InputSpec
from keras.engine.topology import Layer


class DropConnect(Wrapper):
    def __init__(self, layer, dropout=0., **kwargs):
        self.layer = layer
        self.dropout = dropout
        super(DropConnect, self).__init__(layer, **kwargs)
        if 0. < self.dropout < 1.:
            self.uses_learning_phase = True

    def build(self, input_shape):
        if not self.layer.built:
            self.layer.build(input_shape)
            self.layer.built = True
        super(DropConnect, self).build()

    def compute_output_shape(self, input_shape):
        return self.layer.compute_output_shape(input_shape)

    def call(self, x):
        if 0. < self.dropout < 1.:
            self.layer.kernel = K.in_train_phase(K.dropout(self.layer.kernel,
                                                           self.dropout),
                                                 self.layer.kernel)
            self.layer.bias = K.in_train_phase(K.dropout(self.layer.bias,
                                                         self.dropout),
                                               self.layer.bias)
        return self.layer.call(x)


class TemporalMaxPooling(Layer):
    """
    This pooling layer accepts the temporal sequence output by a recurrent layer
    and performs temporal pooling, looking at only the non-masked portion of the
    sequence. The pooling layer converts the entire variable-length hidden
    vector sequence into a single hidden vector.
    Modified from https://github.com/fchollet/keras/issues/2151 so code also
    works on tensorflow backend. Updated syntax to match Keras 2.0 spec.
    Args:
        Just put it on top of an RNN Layer (GRU/LSTM/SimpleRNN) with
        return_sequences=True.  The dimensions are inferred based on the output
        shape of the RNN. 3D tensor with shape: `(samples, steps, features)`.
        input shape: (nb_samples, nb_timesteps, nb_features)
        output shape: (nb_samples, nb_features)
    Examples:
        > x = Bidirectional(GRU(128, return_sequences=True))(x)
        > x = TemporalMaxPooling()(x)
    """
    def __init__(self, **kwargs):
        super(TemporalMaxPooling, self).__init__(**kwargs)
        self.supports_masking = True
        self.input_spec = InputSpec(ndim=3)

    def compute_output_shape(self, input_shape):
        return (input_shape[0], input_shape[2])

    def call(self, x, mask=None):
        if mask is None:
            mask = K.sum(K.ones_like(x), axis=-1)

        #  if masked, set to large negative value so we ignore it when taking
        #  max of the sequence K.switch with tensorflow backend is less useful
        #  than Theano's
        if K.backend() == 'tensorflow':
            mask = K.expand_dims(mask, axis=-1)
            mask = K.tile(mask, (1, 1, K.int_shape(x)[2]))
            masked_data = tf.where(K.equal(mask, K.zeros_like(mask)),
                    K.ones_like(x)*-np.inf, x)  # if masked assume value is -inf
            return K.max(masked_data, axis=1)
        else:  # theano backend
            mask = mask.dimshuffle(0, 1, "x")
            masked_data = K.switch(K.eq(mask, 0), -np.inf, x)
            return masked_data.max(axis=1)

    def compute_mask(self, input, mask):
        # do not pass the mask to the next layers
        return None
