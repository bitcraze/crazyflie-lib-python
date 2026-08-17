---
title: Lighthouse geometry estimation
page_id: lh_geo_estimation
---

This page describes how the geometry estimation for the lighthouse positioning system works in cflib. Geometry estimation is the process of computing the 6-DoF poses (position and orientation) of all base stations in a common coordinate system, from sweep angle measurements taken by a Crazyflie held at a series of known physical positions.

The implementation lives in `cflib/localization/`.

## Estimation process

The intended call sequence to produce a geometry estimation:

**1. Set up the container and solver**

Create the container and start the solver thread. Every time a sample is added to the container, the container increments an internal version number and notifies the solver thread via a `threading.Condition`. The thread wakes up, deep-copies the container data, and runs `estimate_geometry()`. The deep copy means samples can safely be added while a solve is in progress. When the solve completes, `is_done_cb` is called with the result.

```python
container = LhGeoInputContainer(LhDeck4SensorPositions.positions)
container.enable_auto_save()  # optional — serializes samples to a timestamped YAML after each change

solver_thread = LhGeoEstimationManager.SolverThread(
    container,
    is_done_cb=my_solution_callback)
solver_thread.start()
```

**2. Collect the mandatory reference samples**

Use `LighthouseSweepAngleAverageReader` to stream angle packets from the CF and average them. The reader calls back once enough packets have been collected (50 per base station). Construct a `LhCfPoseSample` from the result and store it in the container. At least two base stations must be visible in each sample.

```python
def ready_cb(recorded_angles: dict[int, tuple[int, LighthouseBsVectors]]):
    angles_calibrated = {bs_id: vectors for bs_id, (_, vectors) in recorded_angles.items()}
    sample = LhCfPoseSample(angles_calibrated)
    container.set_origin_sample(sample)  # or whichever setter applies

reader = LighthouseSweepAngleAverageReader(cf, ready_cb)
reader.start_angle_collection()
```

Repeat for each mandatory position, using the appropriate container setter:

```python
container.set_origin_sample(sample)    # defines the world origin
container.set_x_axis_sample(sample)    # must be exactly 1.0 m from origin on positive X-axis
container.append_xy_plane_sample(sample)  # anywhere in Z = 0, away from X-axis
```

Each call wakes the solver thread. The estimation will not succeed until all three are present.

**3. Collect XYZ-space samples**

Use `LighthouseMatchedSweepAngleReader` to capture angles from all visible base stations at a single instant. This is required to correctly constrain base stations that are not both visible from the mandatory positions. Samples can be triggered programmatically at any time, or by using `UserActionDetector` to detect a shake gesture (a quick left–right rotation about the Z-axis followed by holding still) as a hands-free trigger.

```python
container.append_xyz_space_samples([sample])
```

The solver re-runs after each addition. Once the mandatory samples are present and the base station graph is connected, the solver produces a valid `LighthouseGeometrySolution`.

**4. Optionally collect verification samples**

Verification samples are taken the same way as XYZ-space samples but are excluded from the estimation — used only for independent error checking afterwards.

```python
container.append_verification_samples([sample])
```

**5. Use the solution**

The solver thread calls `is_done_cb` with a `LighthouseGeometrySolution` after every solve. When `solution.progress_is_ok` is `True`, the BS poses in `solution.bs_poses` are ready to use. Write them to the Crazyflie or save to file:

```python
# Upload to the Crazyflie
config_writer = LighthouseConfigWriter(cf)
config_writer.write_and_store_config(done_cb, geos=geo_dict)

# Or save to file
LighthouseConfigFileManager.write(file_name, geos=geos, calibs=calibs)
```

## Classes

| Class | File | Role |
|---|---|---|
| `LhGeoInputContainer` | `lighthouse_geo_estimation_manager.py` | Thread-safe store for all collected samples. Notifies waiting threads when data changes. |
| `LhGeoInputContainerData` | `lighthouse_geo_estimation_manager.py` | Plain data holder (sensor positions + sample lists). Deep-copied before each solve to avoid races. |
| `LhGeoEstimationManager` | `lighthouse_geo_estimation_manager.py` | Orchestrates the full estimation pipeline. All methods are class methods; no instance state. |
| `LhGeoEstimationManager.SolverThread` | `lighthouse_geo_estimation_manager.py` | Background thread that re-runs the pipeline whenever the container's version changes. |
| `LhCfPoseSample` | `lighthouse_cf_pose_sample.py` | One measurement at a fixed physical position: calibrated sweep angles per base station, plus cached IPPE solutions. |
| `LhCfPoseSampleWrapper` | `lighthouse_cf_pose_sample.py` | Wraps a `LhCfPoseSample` with estimation-time metadata: sample type, validity status, estimated pose, and error distance. |
| `LighthouseGeometrySolution` | `lighthouse_geometry_solution.py` | Accumulates results and diagnostic information throughout the pipeline. Passed through each stage by reference. |
| `LighthouseInitialEstimator` | `lighthouse_initial_estimator.py` | Produces a rough estimate of all BS and CF poses using IPPE (analytical, no iteration). Starting point for the refining solver. |
| `LighthouseGeometrySolver` | `lighthouse_geometry_solver.py` | Refines the initial estimate with nonlinear least squares (`scipy.optimize.least_squares`, TRF method). |
| `LighthouseSystemAligner` | `lighthouse_system_aligner.py` | Rotates and translates the solution into the user-defined physical coordinate system (origin, X-axis, XY-plane). |
| `LighthouseSystemScaler` | `lighthouse_system_scaler.py` | Scales the solution to metric units using a known reference distance. |
| `LighthouseCrossingBeam` | `lighthouse_utils.py` | Estimates Crazyflie positions and error distances from the geometry, by finding the closest point between pairs of base station rays. Used to produce error statistics and verification poses. |

## Sample types

Each `LhCfPoseSample` is tagged with a `LhCfPoseSampleType` that determines how it is used:

| Type | Purpose | Mandatory |
|---|---|---|
| `ORIGIN` | Defines the world origin (0, 0, 0). Exactly one sample. | Yes |
| `X_AXIS` | A position on the positive X-axis at a known distance from the origin (default 1.0 m). Defines the X direction and provides the scale reference. Exactly one sample. | Yes |
| `XY_PLANE` | One or more positions in the XY-plane (Z = 0), used to constrain the Z direction. | Yes |
| `XYZ_SPACE` | Additional positions anywhere in 3D space, used only to improve the solver's accuracy. Optional; more is better. | No |
| `VERIFICATION` | Positions not used during estimation, only used to independently verify the result afterwards. | No |

`ORIGIN`, `X_AXIS`, and `XY_PLANE` samples are mandatory: if any of these are missing or invalid, estimation cannot proceed. `XYZ_SPACE` samples improve accuracy but are not required. Ambiguous samples (see [Initial estimation](#initial-estimation)) that are mandatory are kept in the pipeline but cause `progress_is_ok` to be set to `False`; non-mandatory ambiguous samples are silently dropped.

## Estimation pipeline

`LhGeoEstimationManager.estimate_geometry()` runs the following steps in order. The `LighthouseGeometrySolution` object is passed through all stages and accumulates results as well as any diagnostic information.

### 1. Data validation

All collected samples are inspected before estimation begins. Samples with fewer than two base stations visible are dropped. Mandatory samples (ORIGIN, X_AXIS, XY_PLANE) with fewer than two visible base stations cause the pipeline to abort. Any issues are recorded on the solution object.

### 2. Initial estimation (IPPE)

`LighthouseInitialEstimator.estimate()` produces a rough geometric solution using IPPE (Infinitesimal Plane-based Pose Estimation), an analytical (non-iterative) method.

For each sample and each visible base station, IPPE produces **two** possible poses due to the planar ambiguity of the lighthouse deck sensors (a mirror solution always exists). The estimator resolves this ambiguity as follows:

1. For every pair of base stations seen together in a sample, compute all four permutations of their relative positions (2 solutions × 2 solutions).
2. Across all samples, cluster the four-way permutations. The correct solution produces a tight cluster; the mirror solutions spread out.
3. Pick the cluster with the most members (majority vote) and use its mean position as the estimated relative BS position.

Using the resolved relative base station positions, the estimator then picks the correct IPPE solution for each sample. Samples where no consistent choice can be made (ambiguity distance > 0.5 m) are flagged `AMBIGUOUS` and dropped if non-mandatory.

Finally, BS poses in the global frame are built iteratively ("onion peeling"): starting from one reference BS, any BS that shares a sample with a known BS can be resolved, repeating until all BSes are placed. If any BS is not reachable through the sample graph (disconnected island), the pipeline aborts.

The output is a rough set of BS poses and CF poses stored in the solution object. This estimate is not accurate enough for flight but is sufficient as the starting point for the refining solver.

### 3. Geometry solver (least squares)

`LighthouseGeometrySolver.solve()` refines the initial estimate using `scipy.optimize.least_squares` with the Trust Region Reflective (TRF) method.

The parameter vector being optimized is:

```
[ bs0_rot_vec(3), bs0_pos(3), bs1_rot_vec(3), bs1_pos(3), ..., cf1_rot_vec(3), cf1_pos(3), ... ]
```

The CF pose for sample 0 (origin) is **not** a parameter; it is fixed at the global origin `[0, 0, 0]` and defines the reference frame for the solver.

For each (sample, base station, sensor, axis) tuple, the residual is the physical distance (in meters) by which a sensor misses the light plane measured at that angle:

```
residual = tan(predicted_angle - measured_angle) × distance(bs, cf)
```

The Jacobian sparsity is provided explicitly: each residual depends only on the pose parameters for one base station and one CF sample, making the system sparse and efficient to optimize. The solver runs for a maximum of 100 function evaluations.

### 4. Alignment

`LighthouseSystemAligner.align()` finds a rigid transformation (rotation + translation, no scale) that maps the solver's internal coordinate frame to the user-defined physical one. It minimizes:

- The origin sample position → maps to `[0, 0, 0]`
- The X-axis sample position → maps to `[X, 0, 0]` with X > 0 (only Y and Z are constrained)
- The XY-plane sample positions → maps to `[X, Y, 0]` (only Z is constrained)

After the optimization, two sanity checks flip the transformation if needed:
- If the mean of the X-axis samples ends up at X < 0, the solution is flipped around the Z-axis.
- If the mean Z of all base stations is negative (below the floor), the solution is flipped around the X-axis.

All BS poses and CF sample poses are transformed into the aligned frame.

### 5. Scaling

`LighthouseSystemScaler.scale_fixed_point()` scales the aligned solution to metric units. It uses the X-axis sample, which the user is expected to have recorded at a known physical distance (default 1.0 m) from the origin along the X-axis. The scale factor is:

```
scale = expected_distance / estimated_distance_to_x_axis_sample
```

All BS and CF poses are scaled uniformly.

### 6. Error statistics

After the full solution is available, error estimates are computed using the crossing beam method (`LighthouseCrossingBeam`):

For each sample, all pairs of base stations are considered. For each pair, the two light "rays" (the intersection line of the two rotating light planes from each BS) are computed in 3D. In a perfect geometry these rays would cross exactly at each sensor; in practice they miss by a small distance. This minimum distance between the two rays across all sensors is the error estimate for that (sample, BS pair).

The worst-case error across all BS pairs is recorded for each sample. Summary statistics (mean, max, std) across all estimation samples are stored as `solution.error_stats`.

The same calculation is run independently for `VERIFICATION` samples and stored as `solution.verification_stats`. Verification samples are also given estimated positions (the midpoint between the closest ray-pair points), so their estimated locations can be shown in a UI.

## Where geometry is stored

`LhGeoInputContainer` holds the raw measurement samples (sweep angles per base station, per position). When auto-save is enabled, the container is serialized to a timestamped YAML session file after every modification. Session files store only samples, not computed BS poses — the BS poses are the output of `estimate_geometry()` and exist only in the returned `LighthouseGeometrySolution`. To persist a configuration, the caller is responsible for writing the resulting poses to the Crazyflie (`LighthouseConfigWriter`) or saving them to file (`LighthouseConfigFileManager`).


## What makes a good geometry estimation

### Requirements

- **At least 2 base stations** must be simultaneously visible in every sample used for estimation. Samples with only one visible BS cannot contribute to the geometry and are filtered out.
- **All base stations must be connected**: every BS must appear together in at least one sample with at least one other BS that is already reachable from the reference BS. A BS that is only ever seen alone, or that forms an isolated island, will cause estimation to fail.
- **All three reference sample types must be present**: origin, X-axis, and at least one XY-plane sample. These are mandatory; missing any of them aborts estimation.
- **The X-axis sample must be placed accurately**: it is the sole source of metric scale, so placement error directly translates to scale error in the entire geometry.

### Accuracy

- **More XYZ_SPACE samples improve accuracy**, especially when they cover different positions and orientations relative to the base stations. Each sample adds constraints to the least-squares system.
- **Spread coverage matters**: samples that are spread out in 3D space and see different combinations of base stations help avoid degenerate configurations and reduce the risk of local minima.
- **Avoid coplanar configurations**: if all CF samples happen to lie in a plane, the IPPE ambiguity is harder to resolve and more samples may be dropped as ambiguous.
- **Calibration data must be applied**: the solver works on `angles_calibrated` (not raw angles). If calibration data is missing or stale, systematic errors will appear in the geometry.

### Interpreting error statistics

After a successful estimation, `solution.error_stats` reports the crossing-beam residuals across all estimation samples:

- `mean`: typical error distance across all samples. Values below ~5 mm indicate a good geometry.
- `max`: worst-case error across all samples. Outliers can indicate a bad sample or a BS pose that did not converge well.
- `std`: spread of errors. A high std relative to the mean suggests inconsistent sample quality.

If `solution.verification_stats` is available, it provides an independent error estimate from samples not used during estimation, which is a more honest measure of predictive accuracy.

`solution.has_converged` indicates whether the least-squares solver met its convergence criterion. A non-converged solution may still be usable but should be treated with more caution; recording more samples and re-estimating is advisable.
