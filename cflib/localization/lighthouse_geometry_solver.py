from collections import namedtuple

import numpy as np
import numpy.typing as npt
import scipy.optimize

from cflib.localization.lighthouse_types import LhCfPoseSample
from cflib.localization.lighthouse_types import Pose

Ray = namedtuple('Ray', ['position', 'vector'])


class LighthouseGeometrySolution:
    """
    Represents a solution from the geometry solver.

    Some data in the object is also used during the solving process for context.
    """

    def __init__(self) -> None:
        # Nr of parameters in a rotation vector
        self.len_rot_vec = 3
        # Nr of parameters
        self.len_pose = 6

        # Nr of base stations
        self.n_bss: int = None
        # Nr of parametrs per base station
        self.n_params_per_bs = self.len_pose

        # Nr of sampled Crazyflie poses
        self.n_cfs: int = None
        # Nr of sampled Crazyflie poses used in the parameter set
        self.n_cfs_in_params: int = None
        # Nr of parameters per Crazyflie pose
        self.n_params_per_cf = self.len_pose

        # Nr of sensors
        self.n_sensors: int = None

        # The maximum nr of iterations to execute when solving the system
        self.max_nr_iter = 10

        self.bs_id_to_index: dict[int, int] = {}
        self.bs_index_to_id: dict[int, int] = {}

        # The solution ######################

        # The estimated poses of the base stations
        self.bs_poses: dict[int, Pose] = {}

        # The raw result from the scipy.optimize.least_squares() function
        self.lsq_result = None

    @property
    def max_iter_reached(self):
        """
        True if the sover was terminated due to reaching the maximum nr of alowed iterations
        """
        result = False
        if self.lsq_result is not None:
            result = self.lsq_result == 0
        return result


class LighthouseGeometrySolver:
    """
    Finds the poses of base stations and Crazyflie samples given a list of matched samples.
    The solver is iterative and uses least squares fitting to minimize the distance from
    the lighthouse sensors to each "ray" measured in the samples.

    The equation system that is solved is defined as:

    Columns are the estimated poses (what we solve for). Each pose is composed of 6 numbers (often referred to as
    parameters in the code): rotation vector (3) and position (3).

    Rows are representing one angle from one base station. The number of rows for each sample is given by the
    number of bs in the sample * n_sensors * 2.

    An examples matrix:

                        bs0_pose, bs1_pose, bs2_pose, bs3_pose, cf1_pose, cf2_pose, ...

    cf0/bs2/sens0/ang0                        X
    cf0/bs2/sens0/ang1                        X
    cf0/bs2/sens1/ang0                        X
    cf0/bs2/sens1/ang1                        X
    ...
    cf0/bs3/sens0/ang0                                  X
    cf0/bs3/sens0/ang1                                  X
    cf0/bs3/sens1/ang0                                  X
    cf0/bs3/sens1/ang1                                  X
    ...
    cf1/bs1/sens0/ang0              X                             X
    cf1/bs1/sens0/ang1              X                             X
    cf1/bs1/sens1/ang0              X                             X
    cf1/bs1/sens1/ang1              X                             X
    ...
    cf1/bs2/sens0/ang0                        X                   X
    cf1/bs2/sens0/ang1                        X                   X
    cf1/bs2/sens1/ang0                        X                   X
    cf1/bs2/sens1/ang1                        X                   X
    ...
    cf2/bs1/sens0/ang0              X                                      X
    cf2/bs1/sens0/ang1              X                                      X
    cf2/bs1/sens1/ang0              X                                      X
    cf2/bs1/sens1/ang1              X                                      X
    ...
    cf2/bs3/sens0/ang0                                  X                  X
    cf2/bs3/sens0/ang1                                  X                  X
    cf2/bs3/sens1/ang0                                  X                  X
    cf2/bs3/sens1/ang1                                  X                  X
    ...

    """

    @classmethod
    def solve(cls, initial_guess_bs_poses: dict[int, Pose], matched_samples: list[LhCfPoseSample],
              sensor_positions: npt.ArrayLike) -> LighthouseGeometrySolution:
        """
        Solve for the pose of base stations and CF samples.
        The pose of the CF in sample 0 defines the global reference frame.

        Iteration is terminated after a fixed number of iteration if acceptable solution
        is found.

        :param initial_guess_bs_poses: Initial guess for the base station poses
        :param matched_samples: List of matched samples, must have been augmented with
                                initial guesses of the CF poses
        :param sensor_positions: Sensor positions (3D), in the CF reference frame
        :return: an instance of LighthouseGeometrySolution
        """
        defs = LighthouseGeometrySolution()

        defs.n_bss = len(initial_guess_bs_poses)
        defs.n_cfs = len(matched_samples)
        defs.n_cfs_in_params = len(matched_samples) - 1
        defs.n_sensors = len(sensor_positions)
        defs.bs_id_to_index, defs.bs_index_to_id = cls._crate_bs_map(initial_guess_bs_poses)

        target_angles = cls._populate_target_angles(matched_samples, defs)
        idx_agl_pr_to_bs, idx_agl_pr_to_cf, idx_agl_pr_to_sens_pos, jac_sparsity = cls._populate_indexes_and_jacobian(
            matched_samples, defs)
        params_bs, params_cfs = cls._populate_initial_guess(initial_guess_bs_poses, matched_samples, defs)

        # Extra arguments passed on to calc_residual()
        args = (defs, idx_agl_pr_to_bs, idx_agl_pr_to_cf, idx_agl_pr_to_sens_pos, target_angles, sensor_positions)

        # Vector to optimize. Composed of base station parameters followed by cf parameters
        x0 = np.hstack((params_bs.ravel(), params_cfs.ravel()))

        result = scipy.optimize.least_squares(cls._calc_residual,
                                              x0,
                                              verbose=0,
                                              jac_sparsity=jac_sparsity,
                                              x_scale='jac',
                                              ftol=1e-8,
                                              method='trf',
                                              max_nfev=defs.max_nr_iter,
                                              args=args)

        defs.lsq_result = result

        bss, cf_poses = cls._params_to_struct(result.x, defs)

        matched_samples[0].estimated_pose = Pose()
        for i, sample in enumerate(matched_samples[1:]):
            sample.estimated_pose = cls._params_to_pose(cf_poses[i], defs)

        defs.bs_poses = {}
        for index, pose in enumerate(bss):
            bs_id = defs.bs_index_to_id[index]
            defs.bs_poses[bs_id] = cls._params_to_pose(pose, defs)

        return defs

    @classmethod
    def _populate_target_angles(cls, matched_samples: list[LhCfPoseSample], defs: LighthouseGeometrySolution
                                ) -> npt.NDArray:
        """
        A np.array of all measured angles, the target angles
        """
        result = []
        for sample in matched_samples:
            for bs_id, angles in sorted(sample.angles_calibrated.items()):
                result += angles.angle_list().tolist()

        return np.array(result)

    @classmethod
    def _populate_indexes_and_jacobian(cls, matched_samples: list[LhCfPoseSample], defs: LighthouseGeometrySolution
                                       ) -> tuple[npt.NDArray, npt.NDArray, npt.NDArray, npt.NDArray]:
        """
        To speed up calculations all operations in the iteration phase are done on np.arrays of equal length (ish),
        the numpy flavour of parallell work. Some data is reused in multiple equations (for instance sensor
        positions) and to avoid copying of data we use np.arrays as indexes. This method creates the necessary
        indexes.

        Since the equation system we are solving is sparse, we can also do a second optimization and only calculate
        the parts of the matrix that are non-zero. We have to provide a matrix containing 1 in the positions where
        the jacobian is non-zero, this matrix is also generated here.
        """
        index_angle_pair_to_bs = []
        index_angle_pair_to_cf = []
        index_angle_pair_to_sensor_base = []

        # Note: Indexes are for angle pairs, that is one set of indexes for two equations in the matrix.
        # Each set of indexes will result in two angles, horizontal and vertical, which means there is one set of
        # indexes per sensor.

        for cf_i, sample in enumerate(matched_samples):
            for bs_id in sorted(sample.angles_calibrated.keys()):
                bs_index = defs.bs_id_to_index[bs_id]
                for sensor_i in range(defs.n_sensors):
                    index_angle_pair_to_cf.append(cf_i)
                    index_angle_pair_to_bs.append(bs_index)
                    index_angle_pair_to_sensor_base.append(sensor_i)

        # Length of residual vector
        len_residual_vec = len(index_angle_pair_to_cf) * 2

        # Length of param vector
        len_param_vec = defs.n_bss * defs.n_params_per_bs + defs.n_cfs_in_params * defs.n_params_per_cf

        # The jac_sparsity matrix should have ones in all locations where data is used in the equations
        jac_sparsity = scipy.sparse.lil_matrix((len_residual_vec, len_param_vec), dtype=int)
        row_i = 0
        n_tot_bs_params = defs.n_bss * defs.n_params_per_bs
        for cf_i, sample in enumerate(matched_samples):
            for bs_id in sorted(sample.angles_calibrated.keys()):
                bs_index = defs.bs_id_to_index[bs_id]
                for sensor_i in range(defs.n_sensors * 2):
                    # Add bs parameters
                    first = bs_index * defs.n_params_per_bs
                    for i in range(first, first + defs.n_params_per_bs):
                        jac_sparsity[row_i, i] = 1
                    # Add cf parameters
                    if cf_i > 0:
                        first = n_tot_bs_params + (cf_i - 1) * defs.n_params_per_cf
                        for i in range(first, first + defs.n_params_per_cf):
                            jac_sparsity[row_i, i] = 1

                    row_i += 1

        return (np.array(index_angle_pair_to_bs),
                np.array(index_angle_pair_to_cf),
                np.array(index_angle_pair_to_sensor_base),
                jac_sparsity)

    @classmethod
    def _populate_initial_guess(cls, initial_guess_bs_poses: list[Pose], matched_samples: list[LhCfPoseSample],
                                defs: LighthouseGeometrySolution) -> tuple[npt.NDArray, npt.NDArray]:
        """
        Generate parameters for base stations and CFs, this is the initial guess we start to iterate from.
        """
        params_bs = np.zeros((len(initial_guess_bs_poses) * defs.n_params_per_bs))
        for bs_id, pose in initial_guess_bs_poses.items():
            index = defs.bs_id_to_index[bs_id] * defs.n_params_per_bs
            params_bs[index:index + defs.n_params_per_bs] = cls._pose_to_params(pose)

        # Skip the first CF pose, it is the definition of the origin and is not a parameter
        params_cfs = []
        for sample in matched_samples[1:]:
            params_cfs.append(cls._pose_to_params(sample.inital_est_pose))

        return params_bs, np.array(params_cfs)

    @classmethod
    def _params_to_struct(cls, params, defs: LighthouseGeometrySolution):
        """
        Convert the params list to two arrays, one for base stations and one for CFs
        """
        bs_param_count = defs.n_bss * defs.n_params_per_bs
        params_bs_poses = params[:bs_param_count].reshape((defs.n_bss, defs.n_params_per_bs))

        params_cf_poses = params[bs_param_count:].reshape((defs.n_cfs_in_params, defs.n_params_per_cf))

        return params_bs_poses, params_cf_poses

    @classmethod
    def _calc_residual(cls, params, defs: LighthouseGeometrySolution, index_angle_pair_to_bs, index_angle_pair_to_cf,
                       index_angle_pair_to_sensor_base, target_angles, sensor_positions):
        """
        Calculate the residual for a set of parameters. The residual is defined as the distance from a sensor to the
        plane given by a measured base station angle.

        :param params: list of parameters for base stations and CFs
        :param defs: information about the context
        :param index_angle_pair_to_bs: index array to index into the base station part of the parameter set
        :param index_angle_pair_to_cf: index array to index into the CF part of the parameter set
        :param index_angle_pair_to_sensor_base: index array to index into the sensor position array
        :param target_angles: the measured angles
        :param sensor_positions: Array with sensor positions
        :return: Array with residuals
        """
        bss, cfs = cls._params_to_struct(params, defs)

        # The first CF pose is defining the origin and is added here
        cfs_full = np.concatenate((np.zeros((1, defs.n_params_per_cf), dtype=float), cfs))

        angle_pairs = cls._poses_to_angle_pairs(bss, cfs_full, sensor_positions, index_angle_pair_to_bs,
                                                index_angle_pair_to_cf, index_angle_pair_to_sensor_base, defs)
        angles = np.ravel(angle_pairs)

        diff = angles - target_angles

        # Calculate the error at the CF positions
        distances_to_cfs = np.repeat(np.linalg.norm(
            bss[index_angle_pair_to_bs] - cfs_full[index_angle_pair_to_cf], axis=1), 2)
        residual = np.tan(diff) * distances_to_cfs

        return residual

    @classmethod
    def _poses_to_angle_pairs(cls, bss, cf_poses, sensor_base_pos, index_angle_pair_to_bs, index_angle_pair_to_cf,
                              index_angle_pair_to_sensor_base, defs: LighthouseGeometrySolution):
        pairs = cls._calc_angle_pairs(bss[index_angle_pair_to_bs], cf_poses[index_angle_pair_to_cf],
                                      sensor_base_pos[index_angle_pair_to_sensor_base], defs)
        return pairs

    @classmethod
    def _calc_angle_pairs(cls, bs_p_a, cf_p_a, sens_pos_p_a, defs: LighthouseGeometrySolution):
        """
        Calculate angle pairs based on base station poses, cf poses and sensor positions

        :param bs_p_a: Poses base stations
        :param cf_p_a: Poses CFs
        :paran sens_pos_p_a: Sensor positions
        :return: angle pairs

        All lists are equally long, one entry per output angle pair
        """
        sensor_points = cls._rotate_translate(sens_pos_p_a, cf_p_a[:, :defs.len_rot_vec], cf_p_a[:, defs.len_rot_vec:])

        # translate and inverse rotate (-rotation vector == inverse rotation)
        points_bs_ref = cls._rotate_translate(sensor_points - bs_p_a[:, defs.len_rot_vec:defs.n_params_per_bs],
                                              -bs_p_a[:, :defs.len_rot_vec],
                                              np.zeros_like(bs_p_a[:, defs.len_rot_vec:defs.n_params_per_bs]))

        angle_pair = np.arctan2(points_bs_ref[:, 1:3], points_bs_ref[:, 0, np.newaxis])
        return angle_pair

    @classmethod
    def _rotate_translate(cls, points, rot_vecs, translations):
        """Rotate points by given rotation vectors and translate

        Rodrigues' rotation formula is used.
        """
        theta = np.linalg.norm(rot_vecs, axis=1)[:, np.newaxis]
        with np.errstate(invalid='ignore'):
            v = rot_vecs / theta
            v = np.nan_to_num(v)
        dot = np.sum(points * v, axis=1)[:, np.newaxis]
        cos_theta = np.cos(theta)
        sin_theta = np.sin(theta)

        return cos_theta * points + sin_theta * np.cross(v, points) + dot * (1 - cos_theta) * v + translations

    @classmethod
    def _pose_to_params(cls, pose: Pose) -> npt.NDArray:
        """
        Convert from Pose to the array format used in the solver
        """
        return np.concatenate((pose.rot_vec, pose.translation))

    @classmethod
    def _params_to_pose(cls, params: npt.ArrayLike, defs: LighthouseGeometrySolution) -> Pose:
        """
        Convert from the array format used in the solver to Pose
        """
        r_vec = params[:defs.len_rot_vec]
        t = params[defs.len_rot_vec:defs.len_pose]
        return Pose.from_rot_vec(R_vec=r_vec, t_vec=t)

    @classmethod
    def _crate_bs_map(cls, initial_guess_bs_poses: dict[int, Pose]) -> tuple[dict[int, int], dict[int, int]]:
        """
        We might have gaps in the list of base station ids that is used in the system, use an index instead
        when refering to a base station. This method creates dictionaries to go from index to base station id,
        or the other way around.

        Base station ids are indexed in an increasing order which means that sorting keys will result
        in sorted indexes as well.
        """
        bs_id_to_index = {}
        bs_index_to_id = {}

        for index, id in enumerate(sorted(initial_guess_bs_poses.keys())):
            bs_id_to_index[id] = index
            bs_index_to_id[index] = id

        return bs_id_to_index, bs_index_to_id

    # TODO

    # @classmethod
    # def estimate_error(cls, bs_poses, matched_samples, sensor_base_pos):
    #     # Estimate the error (in meters) for all CF positions by calculating
    #     # the distance from the ray (defined by measured angles/bs pose) to
    #     # the estimated sensor position
    #     for sample in matched_samples:
    #         cf_pose = sample['pose']
    #         errors = {}
    #         for bs_id, angles in sample['data'].items():
    #             # Only look at sensor 0
    #             horiz = angles[0]
    #             vert = angles[1]

    #             bs_pose = bs_poses[bs_id]
    #             ray = cls._calc_ray(bs_pose, horiz, vert)

    #             sensor_pos = np.dot(cf_pose[0], sensor_base_pos[0]) + cf_pose[1]

    #             error_dist = cls._distance_point_to_ray(sensor_pos, ray)
    #             errors[bs_id] = error_dist
    #         sample['error'] = errors

    #     error_info = cls._analyze_errors(matched_samples)
    #     return error_info

    # @classmethod
    # def _analyze_errors(cls, matched_samples):
    #     error_per_bs = {}
    #     errors = []
    #     for sample in matched_samples:
    #         for bs_id, error in sample['error'].items():
    #             if bs_id not in error_per_bs:
    #                 error_per_bs[bs_id] = []
    #             error_per_bs[bs_id].append(error)
    #             errors.append(error)

    #     error_info = {}
    #     error_info['mean_error'] = np.mean(errors)
    #     error_info['max_error'] = np.max(errors)
    #     error_info['std_error'] = np.std(errors)

    #     error_info['bs'] = {}
    #     for bs_id, errors in error_per_bs.items():
    #         error_info['bs'][bs_id] = {}
    #         error_info['bs'][bs_id]['mean_error'] = np.mean(errors)
    #         error_info['bs'][bs_id]['max_error'] = np.max(errors)
    #         error_info['bs'][bs_id]['std_error'] = np.std(errors)

    #     return error_info

    # @classmethod
    # def _calc_ray(cls, geometry, horiz, vert):
    #     n1 = np.array([np.sin(horiz), -np.cos(horiz), 0.0])
    #     n2 = np.array([-np.sin(vert), 0.0, np.cos(vert)])

    #     n21 = np.cross(n2, n1)
    #     normal = n21 / np.linalg.norm(n21)

    #     R = geometry[0]
    #     vec = np.dot(R, normal)
    #     return Ray(geometry[1], vec)

    # @classmethod
    # def _distance_point_to_ray(cls, point, ray):
    #     return np.linalg.norm(np.cross(ray.vector, ray.position - point)) / np.linalg.norm(ray.vector)
