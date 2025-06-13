
from cflib.localization.lighthouse_cf_pose_sample import LhCfPoseSample
from cflib.localization.lighthouse_types import LhBsCfPoses


class LighthouseGeometrySolution:
    """
    A class to represent the solution of a lighthouse geometry problem.
    """

    def __init__(self):
        # The estimated poses of the base stations and the CF samples
        self.poses = LhBsCfPoses(bs_poses={}, cf_poses=[])

        # Information about errors in the solution
        # TODO krri This data is not well structured
        self.error_info = {}

        # Indicates if the solution converged (True).
        # If it did not converge, the solution is possibly not good enough to use
        self.has_converged = False

        # Progress information stating how far in the solution process we got
        self.progress_info = ""

        # Indicates that all previous steps in the solution process were successful and that the next step
        # can be executed. This is used to determine if the solution process can continue.
        self.progress_is_ok = True

        # Issue descriptions
        self.is_origin_sample_valid = True
        self.origin_sample_info = ''
        self.is_x_axis_samples_valid = True
        self.x_axis_samples_info = ''
        self.is_xy_plane_samples_valid = True
        self.xy_plane_samples_info = ''
        # For the xyz space, there are not any stopping errors, this string may contain information for the user though
        self.xyz_space_samples_info = ''

        # Samples that are mandatory for the solution but where problems were encountered. The tuples contain the sample
        # and a description of the issue. This list is used to extract issue descriptions for the user interface.
        self.mandatory_issue_samples: list[tuple[LhCfPoseSample, str]] = []

    def append_mandatory_issue_sample(self, sample: LhCfPoseSample, issue: str):
        """
        Append a sample with an issue to the list of mandatory issue samples.

        :param sample: The CF pose sample that has an issue.
        :param issue: A description of the issue with the sample.
        """
        self.mandatory_issue_samples.append((sample, issue))
        self.progress_is_ok = False
