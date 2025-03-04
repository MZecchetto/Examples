import KratosMultiphysics
from ROM_TestTrajectory import ROM_Class_test


import KratosMultiphysics.RomApplication as romapp
import json

from KratosMultiphysics.RomApplication.empirical_cubature_method import EmpiricalCubatureMethod
from KratosMultiphysics.RomApplication.randomized_singular_value_decomposition import RandomizedSingularValueDecomposition

import numpy as np
from matplotlib import pyplot as plt
import os






class HROMClass_test(ROM_Class_test):

    def __init__(self, model, project_parameters, correct_cluster, svd_truncation_tolerance, residuals_svd_truncation_tolerance, hard_impose_correct_cluster = False, bases=None, hrom=None):
        super().__init__(model, project_parameters, correct_cluster, hard_impose_correct_cluster, bases, hrom)
        self.svd_truncation_tolerance = svd_truncation_tolerance
        self.residuals_svd_truncation_tolerance = residuals_svd_truncation_tolerance



    def ModifyInitialGeometry(self):
        """Here is the place where the HROM_WEIGHTS are assigned to the selected elements and conditions"""
        super().ModifyInitialGeometry()
        computing_model_part = self._solver.GetComputingModelPart()
        OriginalNumberOfElements = 4916 #TODO, get rid of this, load both elements and condition sets
        WeightsMatrix = np.load(f'HROM/WeightsMatrix_{self.svd_truncation_tolerance}_{self.residuals_svd_truncation_tolerance}.npy')
        ElementsVector = np.load(f'HROM/Elementsvector_{self.svd_truncation_tolerance}_{self.residuals_svd_truncation_tolerance}.npy')

        for i in range(WeightsMatrix.shape[0]):
            if ElementsVector[i] < OriginalNumberOfElements:
                computing_model_part.GetElement(int( ElementsVector[i])+1).SetValue(romapp.HROM_WEIGHT, WeightsMatrix[i,0]  )
            else:
                computing_model_part.GetCondition(int( ElementsVector[i] - OriginalNumberOfElements)+1).SetValue(romapp.HROM_WEIGHT, WeightsMatrix[i,0] )














def HROM(residuals_svd_truncation_tolerance=1e-4, svd_truncation_tolerance=1e-4):

    if not os.path.exists(f'./Results/HROM_{svd_truncation_tolerance}_{residuals_svd_truncation_tolerance}_test.post.bin'):

        with open("ProblemFiles/ProjectParameters_modified.json", 'r') as parameter_file:
            parameters = KratosMultiphysics.Parameters(parameter_file.read())
        global_model = KratosMultiphysics.Model()
        correct_clusters = None

        #loading the bases
        bases = []
        bases = None
        simulation = HROMClass_test(global_model, parameters, correct_clusters, svd_truncation_tolerance, residuals_svd_truncation_tolerance, hard_impose_correct_cluster = False, bases=None, hrom=None )
        simulation.Run()
        np.save(f'Results/HROM_snapshots_test_{svd_truncation_tolerance}_{residuals_svd_truncation_tolerance}.npy',simulation.GetSnapshotsMatrix())


        vy_rom, w_rom = simulation.GetBifuracationData()

        np.save(f'Results/y_velocity_HROM_test_{svd_truncation_tolerance}_{residuals_svd_truncation_tolerance}.npy', vy_rom)
        np.save(f'Results/narrowing_HROM_test_{svd_truncation_tolerance}_{residuals_svd_truncation_tolerance}.npy', w_rom)






def prepare_files(working_path,svd_truncation_tolerance,residuals_svd_truncation_tolerance):
    """pre-pending the absolut path of the files in the Project Parameters"""
    with open(working_path+'/ProblemFiles/ProjectParameters.json','r') as f:
        updated_project_parameters = json.load(f)
        file_input_name = updated_project_parameters["solver_settings"]["fluid_solver_settings"]["model_import_settings"]["input_filename"]
        materials_filename = updated_project_parameters["solver_settings"]["fluid_solver_settings"]["material_import_settings"]["materials_filename"]
        gid_output_name = updated_project_parameters["output_processes"]["gid_output"][0]["Parameters"]["output_name"]

        updated_project_parameters["solver_settings"]["fluid_solver_settings"]["model_import_settings"]["input_filename"] = working_path + '/ProblemFiles/'+ file_input_name
        updated_project_parameters["solver_settings"]["fluid_solver_settings"]["material_import_settings"]["materials_filename"] = working_path +'/ProblemFiles/'+ materials_filename
        updated_project_parameters["output_processes"]["gid_output"][0]["Parameters"]["output_name"] = working_path +f'/Results/HROM_{svd_truncation_tolerance}_{residuals_svd_truncation_tolerance}_test'
        updated_project_parameters["output_processes"]["vtk_output"][0]["Parameters"]["output_path"] = working_path +f'/Results/vtk_HROM_{svd_truncation_tolerance}_{residuals_svd_truncation_tolerance}_test'



    with open(working_path+'/ProblemFiles/ProjectParameters_modified.json','w') as f:
        json.dump(updated_project_parameters, f, indent = 4)











if __name__=="__main__":

    #library for passing arguments to the script from bash
    from sys import argv

    Launch_Simulation = bool(int(argv[1]))
    Number_Of_Clusters= int(argv[2])
    svd_truncation_tolerance= float(argv[3])
    clustering= argv[4]
    overlapping = int(argv[5])
    working_path = argv[6]
    residuals_svd_truncation_tolerance=float(argv[7])

    prepare_files(working_path,svd_truncation_tolerance,residuals_svd_truncation_tolerance)

    HROM(residuals_svd_truncation_tolerance=residuals_svd_truncation_tolerance, svd_truncation_tolerance=svd_truncation_tolerance)
