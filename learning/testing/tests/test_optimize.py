import numpy

from learning import optimize

# NOTE: Not all combinations are tested
##################################
# Problem._get_obj
##################################
def test_optimizer_get_obj_obj_func():
    problem = optimize.Problem(obj_func=lambda x: x)
    assert problem.get_obj(1) == 1

def test_optimizer_get_obj_obj_jac_func():
    problem = optimize.Problem(obj_jac_func=lambda x: (x, x+1))
    assert problem.get_obj(1) == 1

def test_optimizer_get_obj_obj_jac_hess_func():
    problem = optimize.Problem(obj_jac_hess_func=lambda x: (x, x+1, x+2))
    assert problem.get_obj(1) == 1

##################################
# Problem._get_jac
##################################
def test_optimizer_get_jac_jac_func():
    problem = optimize.Problem(jac_func=lambda x: x+1)
    assert problem.get_jac(1) == 2

def test_optimizer_get_jac_obj_jac_func():
    problem = optimize.Problem(obj_jac_func=lambda x: (x, x+1))
    assert problem.get_jac(1) == 2

##################################
# Problem._get_hess
##################################
def test_optimizer_get_hess_hess_func():
    problem = optimize.Problem(hess_func=lambda x: x+2)
    assert problem.get_hess(1) == 3

def test_optimizer_get_hess_obj_hess_func():
    problem = optimize.Problem(obj_hess_func=lambda x: (x, x+2))
    assert problem.get_hess(1) == 3

##################################
# Problem._get_obj_jac
##################################
def test_optimizer_get_obj_jac_obj_jac_func():
    problem = optimize.Problem(obj_jac_func=lambda x: (x, x+1))
    assert problem.get_obj_jac(1) == (1, 2)

def test_optimizer_get_obj_jac_obj_jac_hess_func():
    problem = optimize.Problem(obj_jac_hess_func=lambda x: (x, x+1, x+2))
    assert tuple(problem.get_obj_jac(1)) == (1, 2)

def test_optimizer_get_obj_jac_individual_obj_jac():
    problem = optimize.Problem(obj_func=lambda x: x, jac_func=lambda x: x+1)
    assert tuple(problem.get_obj_jac(1)) == (1, 2)

##################################
# Problem._get_obj_jac_hess
##################################
def test_optimizer_get_obj_jac_hess_obj_jac_hess_func():
    problem = optimize.Problem(obj_jac_hess_func=lambda x: (x, x+1, x+2))
    assert tuple(problem.get_obj_jac_hess(1)) == (1, 2, 3)

def test_optimizer_get_obj_jac_hess_obj_jac_func_individual_hess():
    problem = optimize.Problem(obj_jac_func=lambda x: (x, x+1), hess_func=lambda x: x+2)
    assert tuple(problem.get_obj_jac_hess(1)) == (1, 2, 3)

def test_optimizer_get_obj_jac_hess_obj_hess_func_individual_jac():
    problem = optimize.Problem(obj_hess_func=lambda x: (x, x+2), jac_func=lambda x: x+1)
    assert tuple(problem.get_obj_jac_hess(1)) == (1, 2, 3)

def test_optimizer_get_obj_jac_hess_individual_obj_jac_hess():
    problem = optimize.Problem(obj_func=lambda x: x, jac_func=lambda x: x+1,
                                   hess_func=lambda x: x+2)
    assert tuple(problem.get_obj_jac_hess(1)) == (1, 2, 3)


############################
# SteepestDescentLineSearch
############################
def test_steepest_descent_line_search():
    # Attempt to optimize a simple function with line search
    f = lambda vec: vec[0]**2 + vec[1]**2
    df = lambda vec: numpy.array([2.0*vec[0], 2.0*vec[1]])

    optimizer = optimize.SteepestDescent(step_size_getter=optimize.BacktrackingStepSize())
    problem = optimize.Problem(obj_func=f, jac_func=df)

    # Optimize
    vec = numpy.array([10, 10])
    iteration = 1
    obj_value = 1
    while obj_value > 1e-10 and iteration < 100:
        obj_value, vec = optimizer.next(problem, vec)

    assert obj_value <= 1e-10

def test_steepest_descent_momentum_line_search():
    # Attempt to optimize a simple function with line search
    f = lambda vec: vec[0]**2 + vec[1]**2
    df = lambda vec: numpy.array([2.0*vec[0], 2.0*vec[1]])

    optimizer = optimize.SteepestDescentMomentum(step_size_getter=optimize.BacktrackingStepSize())
    problem = optimize.Problem(obj_func=f, jac_func=df)

    # Optimize
    vec = numpy.array([10, 10])
    iteration = 1
    obj_value = 1
    while obj_value > 1e-10 and iteration < 100:
        obj_value, vec = optimizer.next(problem, vec)

    assert obj_value <= 1e-10

#########################
# Wolfe conditions
#########################
def test_wolfe_conditions():
    # This step at this initial x will minimize f, and must therefore satisfy wolfe
    assert _wolfe_test(numpy.array([1.0, 1.0]), 0.5)

    # This step size will not change obj value, and should not satisfy wolfe
    assert not _wolfe_test(numpy.array([1.0, 1.0]), 1.0)


def _wolfe_test(xk, step_size):
    f = lambda vec: vec[0]**2 + vec[1]**2
    df = lambda vec: numpy.array([2.0*vec[0], 2.0*vec[1]])

    return optimize._wolfe_conditions(step_size, xk, f(xk), df(xk), -df(xk),
                                      f(xk - step_size*df(xk)), df(xk - step_size*df(xk)),
                                      1e-4, 0.1)

def test_armijo_rule():
    # This step at this initial x will minimize f, and must therefore satisfy armijo
    assert _armijo_test(numpy.array([1.0, 1.0]), 0.5)

    # This step size will not change obj value, and should not satisfy armijo
    assert not _armijo_test(numpy.array([1.0, 1.0]), 1.0)

def _armijo_test(xk, step_size):
    f = lambda vec: vec[0]**2 + vec[1]**2
    df = lambda vec: numpy.array([2.0*vec[0], 2.0*vec[1]])

    return optimize._armijo_rule(step_size, f(xk), df(xk), -df(xk), f(xk - step_size*df(xk)), 1e-4)

def test_curvature_condition():
    # This step at this initial x will minimize f, and must therefore satisfy curvature
    assert _curvature_test(numpy.array([1.0, 1.0]), 0.5)

    # Curvature condition requires that slope increases from initial 0.0, it should always fail
    # at 0.0
    assert not _curvature_test(numpy.array([1.0, 1.0]), 0.0)

def _curvature_test(xk, step_size):
    f = lambda vec: vec[0]**2 + vec[1]**2
    df = lambda vec: numpy.array([2.0*vec[0], 2.0*vec[1]])

    return optimize._curvature_condition(df(xk), -df(xk), df(xk - step_size*df(xk)), 0.1)
