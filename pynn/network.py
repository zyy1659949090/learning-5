﻿import numpy
import random
import uuid

from pynn import graph

class Layer(object):
    """A layer of computation for a supervised learning network."""
    attributes = tuple([]) # Attributes for this layer

    requires_prev = tuple([]) # Attributes that are required in the previous layer
    requires_next = tuple([]) # Attributes that are required in the next layer

    def reset(self):
        raise NotImplementedError()

    def activate(self, inputs):
        raise NotImplementedError()

    def get_prev_errors(self, errors, outputs):
        raise NotImplementedError()

    def update(self, inputs, outputs, errors):
        raise NotImplementedError()

    def get_outputs(self, inputs, outputs):
        """Get outputs for previous layer.
        
        Transfer functions should override to properly transform their input
        """
        return None

    def pre_training(self, patterns):
        """Called before each training run.
        
        Optional.
        """

    def post_training(self, patterns):
        """Called after each training run.
        
        Optional.
        """

    def pre_iteration(self, patterns):
        """Called before each training iteration.

        Optional.
        """

    def post_iteration(self, patterns):
        """Called after each training iteration.

        Optional.
        """

class SupportsGrowingLayer(Layer):
    """Layer that supports new neurons by increasing input size.
    
    Adds neurons when GrowingLayer before it raises growth exception.
    """
    attributes = ('supportsGrowing',)

    def add_input(self):
        raise NotImplementedError()

class GrowingLayer(Layer):
    """Layer that can add new neurons, increasing output size.
    
    Raise growth exception when new neuron is added.
    """
    requires_next = ('supportsGrowing',)

class ParallelLayer(Layer):
    """A composite of layers connected in parallel."""

#####################
# Network validation
#####################
def _validate_layers_layers(layers):
    """Assert each element of layers is a Layer."""
    for layer in layers:
        if not isinstance(layer, Layer):
            raise TypeError("layers argument of Network must contain Layer's." \
                             " Instead contains {}.".format(type(layer)))

def _all_in(all_required, values):
    for required in all_required:
        if not required in values:
            return False
    return True

def _validate_requires_next(prev_layer, layer):
    if not _all_in(prev_layer.requires_next, layer.attributes):
        raise TypeError("Layer of type {} must be followed by attributes: {}. " \
                        "It is followed by attributes: " \
                        "{}".format(type(prev_layer), prev_layer.requires_next, 
                                    layer.attributes))

def _validate_requires_prev(next_layer, layer):
    if not _all_in(next_layer.requires_prev, layer.attributes):
        raise TypeError("Layer of type {} must be preceded by attributes: {}. " \
                        "It is preceded by attributes: " \
                        "{}".format(type(next_layer), next_layer.requires_prev, 
                                    layer.attributes))

def _validate_layers_parallel(layers, prev_layer, next_layer):
    """Validate that all layers have the same required features."""
    _validate_layers_layers(layers)

    # Supports prev and next layer
    for i, layer in enumerate(layers):
        if prev_layer:
            _validate_requires_next(prev_layer, layer)

        if next_layer:
            _validate_requires_prev(next_layer, layer)

def _validate_layers_sequence(layers):
    """Validate that layers are valid and each layer matches the next layer."""
    _validate_layers_layers(layers)

    # Check that feature requirements line up
    # Check each lines up with next
    for i in range(len(layers)-1):
        _validate_requires_next(layers[i], layers[i+1])

    # Check each lines up with prev
    for i in range(1, len(layers)):
        _validate_requires_prev(layers[i], layers[i-1])

def _validate_graph(graph_):
    # Graph should have 'I' key
    assert 'I' in graph_.nodes

    # 'I' should have no incoming edges
    for edge in graph_.edges:
        assert edge[1] != 'I'

    # 'O' should have no outgoing edges
    for edge in graph_.edges:
        assert edge[0] != 'O'

    # Graph should have exactly one 'O' value
    O_s = 0
    for edge in graph_.edges:
        if 'O' in edge:
            O_s += 1
    assert O_s == 1

    # All nodes should be able to flow to output
    for node in graph_.nodes:
        # find path from node to 'O'
        assert graph.find_path(graph_.adjacency, node, 'O') is not None


def _layers_to_adjacency_dict(layers):
    """Convert sequence of layers to graph of layers."""
    # First to input
    try:
        layers_dict = {'I': [layers[0]]}
    except IndexError:
        # No layers
        return {'I': ['O']}

    # Each layer to the next
    prev_layer = layers[0]
    for layer in layers[1:]:
        layers_dict[prev_layer] = [layer]
        prev_layer = layer

    # Last to output
    layers_dict[layers[-1]] = ['O']

    return layers_dict


##############################
# Pattern selection functions
##############################
def select_iterative(patterns):
    return patterns


def select_sample(patterns, size=None):
    if size == None:
        size = len(patterns)

    return random.sample(patterns, size)


def select_random(patterns, size=None):
    if size == None:
        size = len(patterns)

    max_index = len(patterns)-1
    return [patterns[random.randint(0, max_index)] for i in range(size)]


class Network(object):
    """A composite of layers connected in sequence."""
    def __init__(self, layers):
        # Allow user to pass a list of layeres connected in sequence
        if isinstance(layers, list):
            layers = _layers_to_adjacency_dict(layers)

        self._graph = graph.Graph(layers)
        _validate_graph(self._graph)
        self._layers = self._graph.nodes - set(['I', 'O'])

        self._activations = {}
        for layer in self._graph.nodes:
            self._activations[layer] = None

        self.logging = True

        # Bookkeeping
        self.iteration = 0

    def _reset_bookkeeping(self):
        self.iteration = 0

    def _incoming_activations(self, layer):
        return [self._activations[incoming] for incoming in 
                self._graph.backwards_adjacency[layer]]

    def _outgoing_errors(self, layer, errors_dict):
        return [errors_dict[outgoing] for outgoing in
                self._graph.adjacency[layer]]

    def activate(self, inputs):
        """Return the network outputs for given inputs."""
        inputs = numpy.array(inputs)
        self._activations = {'I': inputs}
        
        open_list = ['I']
        activated = set(['O']) # So we don't try to activate the output
        while len(open_list) > 0:
            # TODO: need to adjust order of activation, so each layers
            # prerequisites are activated before that layer
            # (look into methods of traversing graphs)
            key = open_list.pop(0)
            for layer in self._graph.adjacency[key]:
                if layer not in activated:
                    ouputs = layer.activate(*self._incoming_activations(layer))
                    activated.add(layer)

                    # Track all activations for learning
                    self._activations[layer] = ouputs

                    # Queue for activation
                    open_list.append(layer)

        # Return activation of the only layer that feeds into output
        return self._activations[self._graph.backwards_adjacency['O'][0]]

    def update(self, inputs, targets):
        # TODO: update to graph system
        """Adjust the network towards the targets for given inputs."""
        outputs = self.activate(inputs)
        outputs_dict = {'O': outputs}

        errors = targets - outputs
        output_errors = errors # For returning
        errors_dict = {'O': errors}

        open_list = ['O']
        updated = set(['I']) # So we don't try to activate the input
        while len(open_list) > 0:
            key = open_list.pop(0)
            for layer in self._graph.backwards_adjacency[key]:
                if layer not in updated:
                    # Pseudo reverse activations, so they are in the right order for
                    # reversed layers list
                    all_inputs = self._incoming_activations(layer)
                    all_errors = self._outgoing_errors(layer, errors_dict)

                    # TODO: adjust so we don't have to change outputs
                    # Then we can uncomment the following line
                    #outputs = self._activations[layer]
                    outputs = outputs_dict[self._graph.adjacency[layer][0]]
                    if outputs is None:
                        outputs = self._activations[layer]

                    # Compute errors for preceding layer before this layers changes
                    errors_dict[layer] = layer.get_prev_errors(all_errors, outputs)
                
                    # Update
                    layer.update(all_inputs, outputs, all_errors)

                    # Transform output for previous layer
                    # TODO: remove this, find another way
                    outputs_dict[layer] = layer.get_outputs(all_inputs, outputs)

                    # Queue this layers connections next
                    open_list.append(layer)

        return output_errors

    def reset(self):
        """Reset every layer in the network."""
        for layer in self._layers:
            layer.reset()

    def test(self, patterns):
        """Print corresponding inputs and outputs from a set of patterns."""
        for p in patterns:
            print(p[0], '->', self.activate(p[0]))

    def get_error(self, pattern):
        """Return the mean squared error (MSE) for a pattern."""
        # Mean squared error
        return numpy.mean(numpy.subtract(self.activate(pattern[0]), pattern[1])**2)

    def get_avg_error(self, patterns):
        """Return the average mean squared error for a set of patterns."""
        error = 0.0        
        for pattern in patterns:
            error = error + self.get_error(pattern)
 
        return error/len(patterns)

    def train(self, patterns, iterations=1000, error_break=0.02,
              pattern_select_func=select_iterative, post_pattern_callback=None):
        """Train network to converge on set of patterns.
        
        Args:
            patterns: A set of (inputs, targets) pairs.
            iterations: Max iterations to train network.
            error_break: Training will end once error is less than this.
            pattern_select_func: Function that takes a set of patterns,
                and returns a set of patterns. Use partial function to embed arguments.
        """
        self._reset_bookkeeping()
        self.reset()

        # For optimization
        track_error = error_break != 0.0 or self.logging

        # Pre-training for each layer
        for layer in self._layers:
            layer.pre_training(patterns)

        # Learn on each pattern for each iteration
        for self.iteration in range(iterations):

            # Pre-iteration for each layer
            for layer in self._layers:
                layer.pre_iteration(patterns)

            # Learn each selected pattern
            error = 0.0
            for pattern in pattern_select_func(patterns):
                # Learn
                errors = self.update(pattern[0], pattern[1])

                # Optional callback for user extension,
                # such as a visualization or history tracking
                if post_pattern_callback:
                    post_pattern_callback(self, pattern)

                # Sum errors
                if track_error:
                    error += numpy.mean(errors**2)

            # Post-iteration for each layer
            for layer in self._layers:
                layer.post_iteration(patterns)
                
            # Logging and breaking
            if track_error:
                error = error / len(patterns)
                if self.logging:
                    print "Iteration {}, Error: {}".format(self.iteration, error)

                # Break early to prevent overtraining
                if error < error_break:
                    break

        # Post-training for each layer
        for layer in self._layers:
            layer.post_training(patterns)

    def serialize(self):
        """Convert network into string.
        
        Returns:
            string; A string representing this network.
        """
        raise NotImplementedError()

    @classmethod
    def unserialize(cls, serialized_network):
        """Convert serialized network into network.

        Returns:
            Network; A Network object.
        """
        raise NotImplementedError()

##########################
# Quick network functions
##########################
def make_mlp(shape, learn_rate=0.5, momentum_rate=0.1):
    """Create a multi-layer perceptron network."""
    from pynn.architecture import transfer
    from pynn.architecture import mlp

    # Create first layer with bias
    add_bias = mlp.AddBias(mlp.Perceptron(shape[0]+1, shape[1], False, 
                                          learn_rate, momentum_rate))
    tanh_transfer = transfer.TanhTransfer()
    layers = {'I': [add_bias],
              add_bias: [tanh_transfer]}

    # Create other layers without bias
    for i in range(1, len(shape)-1):
        perceptron = mlp.Perceptron(shape[i], shape[i+1], False, 
                                           learn_rate, momentum_rate)
        layers[tanh_transfer] = [perceptron]

        tanh_transfer = transfer.TanhTransfer()
        layers[perceptron] = [tanh_transfer]

    layers[tanh_transfer] = ['O']

    return Network(layers)

def make_rbf(inputs, neurons, outputs, learn_rate=1.0, variance=None, normalize=False,
             move_rate=0.1, neighborhood=2, neighbor_move_rate=1.0,):
    """Create a radial-basis function network."""
    from pynn.architecture import transfer
    from pynn.architecture import rbf
    from pynn.architecture import som

    if variance == None:
        variance = 4.0/neurons

    som_ = som.SOM(inputs, neurons, move_rate, neighborhood, neighbor_move_rate)
    gaussian_transfer = transfer.GaussianTransfer(variance)
    gaussian_output = rbf.GaussianOutput(neurons, outputs, learn_rate, normalize=True)
    layers = {'I': [som_],
              som_: [gaussian_transfer],
              gaussian_transfer: [gaussian_output],
              gaussian_output: ['O']}

    return Network(layers)

def make_pbnn():
    from pynn.architecture import pbnn
    from pynn.architecture import transfer

    # Layer that adds all data points before training
    store_inputs = pbnn.StoreInputsLayer()

    # Layer that calculates distances to stored points
    distances = pbnn.DistancesLayer(store_inputs)

    # Gaussian transfer
    # Weighted summation (weighted by output of guassian transfer), sums targets
    # TODO: Normalize output
    gaussian_transfer = transfer.GaussianTransfer()
    weighted_summation = pbnn.WeightedSummationLayer()
    layers = {'I': [distances],
              distances: [gaussian_transfer],
              gaussian_transfer: [weighted_summation],
              weighted_summation: ['O']}

    return Network(layers)