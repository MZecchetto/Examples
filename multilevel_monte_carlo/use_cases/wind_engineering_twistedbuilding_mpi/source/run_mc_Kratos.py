# Import Python libraries
import sys
import os
import json
import time
import pickle

# Import XMC, Kratos, COMPSs
import KratosMultiphysics
import xmc
import xmc.methodDefs_momentEstimator.computeCentralMoments as mdccm
from exaqute import *  # to execute with runcompss


if __name__ == "__main__":

    if len(sys.argv) == 2:
        parametersPath = str(sys.argv[1])  # set path to the parameters
    else:
        parametersPath = "problem_settings/parameters_xmc_asynchronous_mc_twisted.json"

    # read parameters
    with open(parametersPath, "r") as parameter_file:
        parameters = json.load(parameter_file)

    # SolverWrapper
    parameters["solverWrapperInputDictionary"]["qoiEstimator"] = parameters[
        "monteCarloIndexInputDictionary"
    ]["qoiEstimator"]
    # SampleGenerator
    samplerInputDictionary = parameters["samplerInputDictionary"]
    samplerInputDictionary["randomGeneratorInputDictionary"] = parameters[
        "randomGeneratorInputDictionary"
    ]
    samplerInputDictionary["solverWrapperInputDictionary"] = parameters[
        "solverWrapperInputDictionary"
    ]
    # MonteCarloIndex
    monteCarloIndexInputDictionary = parameters["monteCarloIndexInputDictionary"]
    monteCarloIndexInputDictionary["samplerInputDictionary"] = samplerInputDictionary
    # MonoCriterion
    criteriaArray = []
    criteriaInputs = []
    for monoCriterion in parameters["monoCriteriaInputDictionary"]:
        criteriaArray.append(
            xmc.monoCriterion.MonoCriterion(
                parameters["monoCriteriaInputDictionary"][monoCriterion]["criteria"],
                parameters["monoCriteriaInputDictionary"][monoCriterion]["tolerance"],
            )
        )
        criteriaInputs.append(
            [parameters["monoCriteriaInputDictionary"][monoCriterion]["input"]]
        )
    # MultiCriterion
    multiCriterionInputDictionary = parameters["multiCriterionInputDictionary"]
    multiCriterionInputDictionary["criteria"] = criteriaArray
    multiCriterionInputDictionary["inputsForCriterion"] = criteriaInputs
    criterion = xmc.multiCriterion.MultiCriterion(**multiCriterionInputDictionary)
    # ErrorEstimator
    statErrorEstimator = xmc.errorEstimator.ErrorEstimator(
        **parameters["errorEstimatorInputDictionary"]
    )
    # HierarchyOptimiser
    # Set tolerance from stopping criterion
    parameters["hierarchyOptimiserInputDictionary"]["tolerance"] = parameters[
        "monoCriteriaInputDictionary"
    ]["statisticalError"]["tolerance"]
    hierarchyCostOptimiser = xmc.hierarchyOptimiser.HierarchyOptimiser(
        **parameters["hierarchyOptimiserInputDictionary"]
    )
    # EstimationAssembler
    if "expectationAssembler" in parameters["estimationAssemblerInputDictionary"].keys():
        expectationAssembler = xmc.estimationAssembler.EstimationAssembler(
            **parameters["estimationAssemblerInputDictionary"]["expectationAssembler"]
        )
    if "varianceAssembler" in parameters["estimationAssemblerInputDictionary"].keys():
        varianceAssembler = xmc.estimationAssembler.EstimationAssembler(
            **parameters["estimationAssemblerInputDictionary"]["varianceAssembler"]
        )
    # MonteCarloSampler
    monteCarloSamplerInputDictionary = parameters["monteCarloSamplerInputDictionary"]
    monteCarloSamplerInputDictionary[
        "indexConstructorDictionary"
    ] = monteCarloIndexInputDictionary
    monteCarloSamplerInputDictionary["assemblers"] = [
        expectationAssembler,
        varianceAssembler,
    ]
    monteCarloSamplerInputDictionary["errorEstimators"] = [statErrorEstimator]
    # build Monte Carlo sampler object
    mcSampler = xmc.monteCarloSampler.MonteCarloSampler(**monteCarloSamplerInputDictionary)
    # XMCAlgorithm
    XMCAlgorithmInputDictionary = parameters["XMCAlgorithmInputDictionary"]
    XMCAlgorithmInputDictionary["monteCarloSampler"] = mcSampler
    XMCAlgorithmInputDictionary["hierarchyOptimiser"] = hierarchyCostOptimiser
    XMCAlgorithmInputDictionary["stoppingCriterion"] = criterion
    algo = xmc.XMCAlgorithm(**XMCAlgorithmInputDictionary)

    time_start = time.time()
    algo = xmc.XMCAlgorithm(**XMCAlgorithmInputDictionary)
    if parameters["solverWrapperInputDictionary"]["asynchronous"] is True:
        algo.runAsynchronousXMC()
    else:
        algo.runXMC()
    time_end = time.time()
    print("[SCREENING] computational time:", time_end - time_start)

    ########################################################################################################################################################################################################
    ########################################################################################################################################################################################################
    ########################################################################################################################################################################################################

    # retrieve project parameters and mdpa
    with open(
        parameters["solverWrapperInputDictionary"]["projectParametersPath"][0], "r"
    ) as parameter_file:
        project_parameters = json.load(parameter_file)
    pickled_model = algo.monteCarloSampler.indices[0].sampler.solvers[0].pickled_model[0]
    try:
        serialized_model = pickle.loads(get_value_from_remote(pickled_model[0]))
    except:
        serialized_model = pickle.loads(get_value_from_remote(pickled_model))
    current_model = KratosMultiphysics.Model()
    serialized_model.Load("ModelSerialization", current_model)
    model_part_of_interest = "FluidModelPart.NoSlip3D_structure"

    # writing to file a dictionary
    qoi_dict = {}
    # save Kratos project parameters and mdpa info
    qoi_dict["KratosMultiphysics_project_parameters"] = {
        "project_parameters": project_parameters
    }
    qoi_dict["model_part"] = {
        "mdpa_names": current_model.GetModelPartNames(),
        "mdpa_of_interest": model_part_of_interest,
    }
    # save xmc parameters
    if len(sys.argv) == 2:
        parametersPath_dict = str(sys.argv[1])  # set path to the parameters
    else:
        parametersPath_dict = (
            "problem_settings/parameters_xmc_asynchronous_mc_CAARC3d_Fractional.json"
        )
    # read parameters
    with open(parametersPath_dict, "r") as parameter_file_dict:
        parameters_dict = json.load(parameter_file_dict)
    qoi_dict["XMC_parameters"] = {"parameters": parameters_dict}

    # add legend
    qoi_dict["qoi_id_legend"] = {"index_legend": {}}
    qoi_dict["qoi_id_legend"]["index_legend"] = {
        "qoi_id": "qoi id",
        "index": "Monte Carlo index/level",
        "instances": "number of samples/contributions for current level",
        "Sa": "power sum order a",
        "ha": "moment order a",
        "type": "qoi type",
        "tag": "physical quantity name",
        "node_id": "mesh node id",
        "node_coordinates": "coordinates of the node",
    }

    # save time averaged drag
    for qoi_counter in range(0, 1):
        qoi_dict["qoi_id_" + str(qoi_counter)] = {
            "index_" + str(index): {} for index in range(len(algo.monteCarloSampler.indices))
        }
        for index in range(len(algo.monteCarloSampler.indices)):
            algo.monteCarloSampler.indices[index].qoiEstimator[
                qoi_counter
            ] = get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]
            )
            sample_counter = (
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._sampleCounter
            )
            S1 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[0][0]
                )
            )
            S2 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[1][0]
                )
            )
            S3 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[2][0]
                )
            )
            S4 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[3][0]
                )
            )
            S5 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[4][0]
                )
            )
            S6 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[5][0]
                )
            )
            S7 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[6][0]
                )
            )
            S8 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[7][0]
                )
            )
            S9 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[8][0]
                )
            )
            S10 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[9][0]
                )
            )
            h1 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderOneDimensionZero(S1, sample_counter)
                )
            )
            h2 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderTwoDimensionZero(S1, S2, sample_counter)
                )
            )
            qoi_dict["qoi_id_" + str(qoi_counter)]["index_" + str(index)] = {
                "qoi_id": qoi_counter,
                "index": index,
                "instances": sample_counter,
                "S1": S1,
                "S2": S2,
                "S3": S3,
                "S4": S4,
                "S5": S5,
                "S6": S6,
                "S7": S7,
                "S8": S8,
                "S9": S9,
                "S10": S10,
                "h1": h1,
                "h2": h2,
                "type": "time_averaged_quantity",
                "tag": "drag_force_x",
            }

    # save time averaged base moment
    for qoi_counter in range(1, 2):
        qoi_dict["qoi_id_" + str(qoi_counter)] = {
            "index_" + str(index): {} for index in range(len(algo.monteCarloSampler.indices))
        }
        for index in range(len(algo.monteCarloSampler.indices)):
            algo.monteCarloSampler.indices[index].qoiEstimator[
                qoi_counter
            ] = get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]
            )
            sample_counter = (
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._sampleCounter
            )
            S1 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[0][0]
                )
            )
            S2 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[1][0]
                )
            )
            S3 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[2][0]
                )
            )
            S4 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[3][0]
                )
            )
            S5 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[4][0]
                )
            )
            S6 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[5][0]
                )
            )
            S7 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[6][0]
                )
            )
            S8 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[7][0]
                )
            )
            S9 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[8][0]
                )
            )
            S10 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    .powerSums[9][0]
                )
            )
            h1 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderOneDimensionZero(S1, sample_counter)
                )
            )
            h2 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderTwoDimensionZero(S1, S2, sample_counter)
                )
            )
            qoi_dict["qoi_id_" + str(qoi_counter)]["index_" + str(index)] = {
                "qoi_id": qoi_counter,
                "index": index,
                "instances": sample_counter,
                "S1": S1,
                "S2": S2,
                "S3": S3,
                "S4": S4,
                "S5": S5,
                "S6": S6,
                "S7": S7,
                "S8": S8,
                "S9": S9,
                "S10": S10,
                "h1": h1,
                "h2": h2,
                "type": "time_averaged_quantity",
                "tag": "base_moment_z",
            }

    # save time averaged pressure field
    qoi_counter = qoi_counter + 1
    qoi_dict["qoi_id_" + str(qoi_counter)] = {
        "member_" + str(member): {}
        for member in range(
            algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._variableDimension
        )
    }
    for member in range(
        algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._variableDimension
    ):
        qoi_dict["qoi_id_" + str(qoi_counter)]["member_" + str(member)] = {
            "index_" + str(index): {} for index in range(len(algo.monteCarloSampler.indices))
        }
        for index in range(len(algo.monteCarloSampler.indices)):
            algo.monteCarloSampler.indices[index].qoiEstimator[
                qoi_counter
            ] = get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]
            )
            sample_counter = (
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._sampleCounter
            )
            S1 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["1"][member]
                )
            )
            S2 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["2"][member]
                )
            )
            S3 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["3"][member]
                )
            )
            S4 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["4"][member]
                )
            )
            S5 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["5"][member]
                )
            )
            S6 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["6"][member]
                )
            )
            S7 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["7"][member]
                )
            )
            S8 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["8"][member]
                )
            )
            S9 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["9"][member]
                )
            )
            S10 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["10"][member]
                )
            )
            h1 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderOneDimensionZero(S1, sample_counter)
                )
            )
            h2 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderTwoDimensionZero(S1, S2, sample_counter)
                )
            )
            node_id = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[6]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[6]._sampleCounter
            )
            node_x = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[7]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[7]._sampleCounter
            )
            node_y = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[8]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[8]._sampleCounter
            )
            node_z = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[9]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[9]._sampleCounter
            )
            qoi_dict["qoi_id_" + str(qoi_counter)]["member_" + str(member)][
                "index_" + str(index)
            ] = {
                "qoi_id": qoi_counter,
                "member": member,
                "index": index,
                "instances": sample_counter,
                "S1": S1,
                "S2": S2,
                "S3": S3,
                "S4": S4,
                "S5": S5,
                "S6": S6,
                "S7": S7,
                "S8": S8,
                "S9": S9,
                "S10": S10,
                "h1": h1,
                "h2": h2,
                "type": "scalar_quantity",
                "tag": "pressure coefficent",
                "node_id": node_id,
                "node_coordinates": [node_x, node_y, node_z],
            }

    # save time series drag
    qoi_counter = qoi_counter + 1
    qoi_dict["qoi_id_" + str(qoi_counter)] = {
        "index_" + str(index): {} for index in range(len(algo.monteCarloSampler.indices))
    }
    for index in range(len(algo.monteCarloSampler.indices)):
        algo.monteCarloSampler.indices[index].qoiEstimator[
            qoi_counter
        ] = get_value_from_remote(
            algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]
        )
        sample_counter = get_value_from_remote(
            algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._sampleCounter
        )
        S1 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[0][0]
            )
        )
        S2 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[1][0]
            )
        )
        S3 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[2][0]
            )
        )
        S4 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[3][0]
            )
        )
        S5 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[4][0]
            )
        )
        S6 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[5][0]
            )
        )
        S7 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[6][0]
            )
        )
        S8 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[7][0]
            )
        )
        S9 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[8][0]
            )
        )
        S10 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[9][0]
            )
        )
        h1 = float(
            get_value_from_remote(
                mdccm.computeCentralMomentsOrderOneDimensionZero(S1, sample_counter)
            )
        )
        h2 = float(
            get_value_from_remote(
                mdccm.computeCentralMomentsOrderTwoDimensionZeroBiased(S1, S2, sample_counter)
            )
        )
        qoi_dict["qoi_id_" + str(qoi_counter)]["index_" + str(index)] = {
            "qoi_id": qoi_counter,
            "index": index,
            "instances": sample_counter,
            "S1": S1,
            "S2": S2,
            "S3": S3,
            "S4": S4,
            "S5": S5,
            "S6": S6,
            "S7": S7,
            "S8": S8,
            "S9": S9,
            "S10": S10,
            "h1": h1,
            "h2": h2,
            "type": "time_series_quantity",
            "tag": "drag_force_x",
        }

    # save time series base moment
    qoi_counter = qoi_counter + 1
    qoi_dict["qoi_id_" + str(qoi_counter)] = {
        "index_" + str(index): {} for index in range(len(algo.monteCarloSampler.indices))
    }
    for index in range(len(algo.monteCarloSampler.indices)):
        algo.monteCarloSampler.indices[index].qoiEstimator[
            qoi_counter
        ] = get_value_from_remote(
            algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]
        )
        sample_counter = get_value_from_remote(
            algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._sampleCounter
        )
        S1 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[0][0]
            )
        )
        S2 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[1][0]
            )
        )
        S3 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[2][0]
            )
        )
        S4 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[3][0]
            )
        )
        S5 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[4][0]
            )
        )
        S6 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[5][0]
            )
        )
        S7 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[6][0]
            )
        )
        S8 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[7][0]
            )
        )
        S9 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[8][0]
            )
        )
        S10 = float(
            get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter].powerSums[9][0]
            )
        )
        h1 = float(
            get_value_from_remote(
                mdccm.computeCentralMomentsOrderOneDimensionZero(S1, sample_counter)
            )
        )
        h2 = float(
            get_value_from_remote(
                mdccm.computeCentralMomentsOrderTwoDimensionZeroBiased(S1, S2, sample_counter)
            )
        )
        qoi_dict["qoi_id_" + str(qoi_counter)]["index_" + str(index)] = {
            "qoi_id": qoi_counter,
            "index": index,
            "instances": sample_counter,
            "S1": S1,
            "S2": S2,
            "S3": S3,
            "S4": S4,
            "S5": S5,
            "S6": S6,
            "S7": S7,
            "S8": S8,
            "S9": S9,
            "S10": S10,
            "h1": h1,
            "h2": h2,
            "type": "time_series_quantity",
            "tag": "base_moment_z",
        }

    # save time series pressure field
    qoi_counter = qoi_counter + 1
    qoi_dict["qoi_id_" + str(qoi_counter)] = {
        "member_" + str(member): {}
        for member in range(
            algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._variableDimension
        )
    }
    for member in range(
        algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._variableDimension
    ):
        qoi_dict["qoi_id_" + str(qoi_counter)]["member_" + str(member)] = {
            "index_" + str(index): {} for index in range(len(algo.monteCarloSampler.indices))
        }
        for index in range(len(algo.monteCarloSampler.indices)):
            algo.monteCarloSampler.indices[index].qoiEstimator[
                qoi_counter
            ] = get_value_from_remote(
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]
            )
            sample_counter = (
                algo.monteCarloSampler.indices[index].qoiEstimator[qoi_counter]._sampleCounter
            )
            S1 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["1"][member]
                )
            )
            S2 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["2"][member]
                )
            )
            S3 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["3"][member]
                )
            )
            S4 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["4"][member]
                )
            )
            S5 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["5"][member]
                )
            )
            S6 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["6"][member]
                )
            )
            S7 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["7"][member]
                )
            )
            S8 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["8"][member]
                )
            )
            S9 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["9"][member]
                )
            )
            S10 = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[qoi_counter]
                    ._powerSums["10"][member]
                )
            )
            h1 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderOneDimensionZero(S1, sample_counter)
                )
            )
            h2 = float(
                get_value_from_remote(
                    mdccm.computeCentralMomentsOrderTwoDimensionZero(S1, S2, sample_counter)
                )
            )
            node_id = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[6]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[6]._sampleCounter
            )
            node_x = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[7]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[7]._sampleCounter
            )
            node_y = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[8]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[8]._sampleCounter
            )
            node_z = float(
                get_value_from_remote(
                    algo.monteCarloSampler.indices[index]
                    .qoiEstimator[9]
                    ._powerSums["1"][member]
                )
                / algo.monteCarloSampler.indices[index].qoiEstimator[9]._sampleCounter
            )
            qoi_dict["qoi_id_" + str(qoi_counter)]["member_" + str(member)][
                "index_" + str(index)
            ] = {
                "qoi_id": qoi_counter,
                "member": member,
                "index": index,
                "instances": sample_counter,
                "S1": S1,
                "S2": S2,
                "S3": S3,
                "S4": S4,
                "S5": S5,
                "S6": S6,
                "S7": S7,
                "S8": S8,
                "S9": S9,
                "S10": S10,
                "h1": h1,
                "h2": h2,
                "type": "scalar_quantity",
                "tag": "pressure coefficent",
                "node_id": node_id,
                "node_coordinates": [node_x, node_y, node_z],
            }

    # save to file
    with open(
        "power_sums_outputs/MC_asynchronous_power_sums_" + str(time.time()) + ".json", "w"
    ) as f:
        json.dump(qoi_dict, f, indent=2)

