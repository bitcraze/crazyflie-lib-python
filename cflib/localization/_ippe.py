import numpy as np

# Copyright (c) 2016 The Python Packaging Authority (PyPA)

# Permission is hereby granted, free of charge, to any person obtaining a copy of
# this software and associated documentation files (the "Software"), to deal in
# the Software without restriction, including without limitation the rights to
# use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
# of the Software, and to permit persons to whom the Software is furnished to do
# so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# This code has been copied from https://github.com/royxue/ippe_py and slightly modified
# to avoid a dependency to Open CV and to collect all functionality in one file.

# The code uses a coordinate system as defined by Open CV.

# The code is based on the paper
# @article{ year={2014}, issn={0920-5691}, journal={International Journal of Computer Vision}, volume={109}, number={3}, doi={10.1007/s11263-014-0725-5}, title={Infinitesimal Plane-Based Pose Estimation}, url={http://dx.doi.org/10.1007/s11263-014-0725-5}, publisher={Springer US}, keywords={Plane; Pose; SfM; PnP; Homography}, author={Collins, Toby and Bartoli, Adrien}, pages={252-286}, language={English} }  # noqa


def mat_run(U, Q, hEstMethod='DLT'):
    """
    The solution to Perspective IPPE with point correspondences computed
    between points in world coordinates on the plane z=0, and normalised points in the
    camera's image.

    Parameters
    ----------
    U: 2xN or 3xN matrix holding the model points in world coordinates. If U
        is 2xN then the points are defined in world coordinates on the plane z=0

    Q: 2xN matrix holding the points in the image. These are in normalised
        pixel coordinates. That is, the effects of the camera's intrinsic matrix
        and lens distortion are corrected, so that the Q projects with a perfect
        pinhole model.

    hEstMethod: the homography estimation method, by default Direct Linear Transform is used,
        from Peter Kovesi's implementation at http://www.csse.uwa.edu.au/~pk.


    Return
    ---------
    IPPEPoses: A Python dictionary that contains 2 sets of pose solution from IPPE including rotation matrix
        translation matrix, and reprojection error
    """
    if hEstMethod not in ['Harker', 'DLT']:
        print('hEstMethod Error')

    # Inputs shape checking
    assert (U.shape[0] == 2 or U.shape[0] == 3)
    assert (U.shape[1] == Q.shape[1])
    assert (Q.shape[0] == 2)

    n = U.shape[1]
    modelDims = U.shape[0]

    Uuncentred = U

    if modelDims == 2:
        # Zero center the model points
        # Zero center the model points
        Pbar = np.vstack((np.mean(U, axis=1, keepdims=True), 0))
        U[0, :] = U[0, :]-Pbar[0]
        U[1, :] = U[1, :]-Pbar[1]
    else:
        # Rotate the model points onto the plane z=0 and zero center them
        Pbar = np.mean(U[:1])
        MCenter = np.eye(4)
        MCenter[0:3, -1] = -Pbar
        U_ = MCenter[0:3, :].dot(np.vstack((U, np.ones((1, U.shape[1])))))
        modelRotation, sigs, _ = np.linalg.svd(U_.dot(U_.T))
        modelRotation = modelRotation.T

        modelRotation = np.hstack((np.vstack((modelRotation, np.array([0, 0, 0]))), np.array([[0], [0], [0], [1]])))
        Mcorrective = modelRotation.dot(MCenter)
        U = Mcorrective[0:2, :].dot(np.vstack((U, np.ones((1, U.shape[1])))))

    # TODO: Add support for Harker function
    # Compute the model to image homography
    if hEstMethod == 'DLT':
        _U = np.vstack((U, np.ones((1, n))))
        _Q = np.vstack((Q, np.ones((1, n))))
        H = homography2d(_U, _Q)

    H = H/H[2, 2]

    # Compute the Jacobian J of the homography at (0,0)
    J = np.zeros((2, 2))
    J[0, 0] = H[0, 0]-H[2, 0]*H[0, 2]
    J[0, 1] = H[0, 1]-H[2, 1]*H[0, 2]
    J[1, 0] = H[1, 0]-H[2, 0]*H[1, 2]
    J[1, 1] = H[1, 1]-H[2, 1]*H[1, 2]

    # Compute rotate solution
    v = np.vstack((H[0, 2], H[1, 2]))
    [R1, R2, _] = IPPE_dec(v, J)

    # compute the translation solution
    t1_ = estT(R1, U, Q)
    t2_ = estT(R2, U, Q)

    if modelDims == 2:
        t1 = np.hstack((R1, t1_)).dot(np.vstack((-Pbar, 1)))
        t2 = np.hstack((R2, t2_)).dot(np.vstack((-Pbar, 1)))
    else:
        M1 = np.hstack((R1, t1_))
        M1 = np.vstack((M1, np.array([0, 0, 0, 1])))
        M2 = np.hstack((R2, t2_))
        M2 = np.vstack((M2, np.array([0, 0, 0, 1])))
        M1 = M1.dot(Mcorrective)
        M2 = M2.dot(Mcorrective)
        R1 = M1[0:3, 0:3]
        R2 = M2[0:3, 0:3]
        t1 = M1[0:3, -1]
        t2 = M2[0:3, -1]

    [reprojErr1, reprojErr2] = computeReprojErrs(R1, R2, t1, t2, Uuncentred, Q)

    if reprojErr1 > reprojErr2:
        [R1, R2, t1, t2, reprojErr1, reprojErr2] = swapSolutions(R1, R2, t1, t2, reprojErr1, reprojErr2)

    IPPEPoses = {}
    IPPEPoses['R1'] = R1
    IPPEPoses['t1'] = t1
    IPPEPoses['R2'] = R2
    IPPEPoses['t2'] = t2
    IPPEPoses['reprojError1'] = reprojErr1
    IPPEPoses['reprojError2'] = reprojErr2

    return IPPEPoses


def computeReprojErrs(R1, R2, t1, t2, U, Q):
    """
    Computes the reprojection errors for the two solutions generated by IPPE.
    """

    # transform model points to camera coordinates and project them onto the image
    if U.shape[0] == 2:
        PCam1 = R1[:, 0:2].dot(U)
        PCam2 = R2[:, 0:2].dot(U[0:2, :])
    else:
        PCam1 = R1.dot(U)
        PCam2 = R2.dot(U)

    PCam1[0, :] = PCam1[0, :] + t1[0]
    PCam1[1, :] = PCam1[1, :] + t1[1]
    PCam1[2, :] = PCam1[2, :] + t1[2]

    PCam2[0, :] = PCam2[0, :] + t2[0]
    PCam2[1, :] = PCam2[1, :] + t2[1]
    PCam2[2, :] = PCam2[2, :] + t2[2]

    Qest_1 = PCam1/np.vstack((PCam1[2, :], PCam1[2, :], PCam1[2, :]))
    Qest_2 = PCam2/np.vstack((PCam2[2, :], PCam2[2, :], PCam2[2, :]))

    # Compute reprojection errors:
    reprojErr1 = np.linalg.norm(Qest_1[0:2, :]-Q)
    reprojErr2 = np.linalg.norm(Qest_2[0:2, :]-Q)

    return [reprojErr1, reprojErr2]


def estT(R, psPlane, Q):
    """
    Computes the least squares estimate of translation given the rotation solution.
    """
    if psPlane.shape[0] == 2:
        psPlane = np.vstack((psPlane, np.zeros((1, psPlane.shape[1]))))

    Ps = R.dot(psPlane)

    numPts = psPlane.shape[1]
    Ax = np.zeros((numPts, 3))
    bx = np.zeros((numPts, 1))

    Ay = np.zeros((numPts, 3))
    by = np.zeros((numPts, 1))

    Ax[:, 0] = 1
    Ax[:, 2] = -Q[0, :]
    bx[:] = (Q[0, :]*Ps[2, :] - Ps[0, :]).reshape(4, 1)

    Ay[:, 1] = 1
    Ay[:, 2] = -Q[1, :]
    by[:] = (Q[1, :]*Ps[2, :] - Ps[1, :]).reshape(4, 1)

    A = np.vstack((Ax, Ay))
    b = np.vstack((bx, by))

    AtA = A.conj().T.dot(A)
    Atb = A.conj().T.dot(b)

    Ainv = IPPE_inv33(AtA)
    t = Ainv.dot(Atb)
    return t


def swapSolutions(R1_, R2_, t1_, t2_, reprojErr1_, reprojErr2_):
    """
    Swap the solutions
    """

    R1 = R2_
    t1 = t2_
    reprojErr1 = reprojErr2_

    R2 = R1_
    t2 = t1_
    reprojErr2 = reprojErr1_

    return [R1, R2, t1, t2, reprojErr1, reprojErr2]


def IPPE_inv33(A):
    """
    Computes the inverse of a 3x3 matrix, assuming it is full-rank.
    """
    a11 = A[0, 0]
    a12 = A[0, 1]
    a13 = A[0, 2]

    a21 = A[1, 0]
    a22 = A[1, 1]
    a23 = A[1, 2]

    a31 = A[2, 0]
    a32 = A[2, 1]
    a33 = A[2, 2]

    Ainv = np.vstack((np.array([a22*a33 - a23*a32, a13*a32 - a12*a33, a12*a23 - a13*a22]),
                      np.array([a23*a31 - a21*a33, a11*a33 - a13*a31, a13*a21 - a11*a23]),
                      np.array([a21*a32 - a22*a31, a12*a31 - a11*a32, a11*a22 - a12*a21])))
    Ainv = Ainv/(a11*a22*a33 - a11*a23*a32 - a12*a21*a33 + a12*a23*a31 + a13*a21*a32 - a13*a22*a31)
    return Ainv


def IPPE_dec(v, J):
    """
    Calculate 2 solutions to rotate from J Jacobian of the model-to-plane homography H

    Parameters
    ----------
    v: 2x1 vector holding the point in normalised pixel coordinates which maps by H^-1 to
        the point (0,0,0) in world coordinates.
    J: 2x2 Jacobian matrix of H at (0,0).

    Return
    ---------
    R1: 3x3 Rotation matrix (first solution)
    R2: 3x3 Rotation matrix (second solution)
    gamma: The positive real-valued inverse-scale factor.
    """

    # Calculate the correction rotation Rv
    t = np.linalg.norm(v)

    if t < np.finfo(float).eps:
        # the plane is fronto-parallel to the camera, so set the corrective rotation Rv to identity.
        # There will be only one solution to pose.
        Rv = np.eye(3)
    else:
        # the plane is not fronto-parallel to the camera, so set the corrective rotation Rv
        s = np.linalg.norm(np.vstack((v, 1)))
        costh = 1./s
        sinth = np.sqrt(1-1./s**2)
        Kcrs = 1./t*(np.vstack([np.hstack([np.zeros((2, 2)), v]), np.hstack([-v.T, np.zeros((1, 1))])]))
        Rv = np.eye(3) + sinth*Kcrs + (1.-costh)*Kcrs.dot(Kcrs)

    # Set up 2x2 SVD decomposition
    B = np.hstack((np.eye(2), -v)).dot(Rv[:, 0:2])
    dt = B[0, 0]*B[1, 1] - B[0, 1]*B[1, 0]
    Binv = np.vstack([np.hstack([B[1, 1]/dt, -B[0, 1]/dt]), np.hstack([-B[1, 0]/dt, B[0, 0]/dt])])
    A = Binv.dot(J)

    # Compute the largest singular value of A
    AAT = A.dot(A.T)
    gamma = np.sqrt(1./2*(AAT[0, 0] + AAT[1, 1] + np.sqrt((AAT[0, 0]-AAT[1, 1])**2 + 4*AAT[0, 1]**2)))

    # Reconstruct the full rotation matrices
    R22_tild = A/gamma

    h = np.eye(2)-R22_tild.T.dot(R22_tild)
    b = np.vstack((np.sqrt(h[0, 0]), np.sqrt(h[1, 1])))
    if h[0, 1] < 0:
        b[1] = -b[1]
    v1 = np.vstack((R22_tild[:, 0:1], np.array([b[0]])))
    v2 = np.vstack((R22_tild[:, 1:2], np.array([b[1]])))
    d = IPPE_crs(v1, v2)
    c = d[0:2]
    a = d[2]
    R1 = Rv.dot(np.vstack((np.hstack((R22_tild, c)), np.hstack((b.conj().T, np.array([a]))))))
    R2 = Rv.dot(np.vstack((np.hstack((R22_tild, -c)), np.hstack((-b.conj().T, np.array([a]))))))

    return [R1, R2, gamma]


def IPPE_crs(v1, v2):
    """
    3D cross product for vectors v1 and v2
    """
    v3 = np.zeros((3, 1))
    v3[0] = v1[1]*v2[2]-v1[2]*v2[1]
    v3[1] = v1[2]*v2[0]-v1[0]*v2[2]
    v3[2] = v1[0]*v2[1]-v1[1]*v2[0]

    return v3


def homography2d(x1, x2):
    """
    Direct Linear Transform

    Input:
    x1: 3xN set of homogeneous points
    x2: 3xN set of homogeneous points such that x1<->x2

    Returns:
    H: the 3x3 homography such that x2 = H*x1
    """
    [x1, T1] = normalise2dpts(x1)
    [x2, T2] = normalise2dpts(x2)

    Npts = x1.shape[1]

    A = np.zeros((3*Npts, 9))

    O = np.zeros(3)  # noqa

    for i in range(0, Npts):
        X = x1[:, i].T
        x = x2[0, i]
        y = x2[1, i]
        w = x2[2, i]
        A[3*i, :] = np.array([O, -w*X, y*X]).reshape(1, 9)
        A[3*i+1, :] = np.array([w*X, O, -x*X]).reshape(1, 9)
        A[3*i+2, :] = np.array([-y*X, x*X, O]).reshape(1, 9)

    [U, D, Vh] = np.linalg.svd(A)
    V = Vh.T

    H = V[:, 8].reshape(3, 3)

    H = np.linalg.solve(T2, H)
    H = H.dot(T1)

    return H


def normalise2dpts(pts):
    """
    Function translates and normalises a set of 2D homogeneous points
    so that their centroid is at the origin and their mean distance from
    the origin is sqrt(2).  This process typically improves the
    conditioning of any equations used to solve homographies, fundamental
    matrices etc.


    Inputs:
    pts: 3xN array of 2D homogeneous coordinates

    Returns:
    newpts: 3xN array of transformed 2D homogeneous coordinates.  The
            scaling parameter is normalised to 1 unless the point is at
            infinity.
    T: The 3x3 transformation matrix, newpts = T*pts
    """
    if pts.shape[0] != 3:
        print('Input shoud be 3')

    finiteind = np.nonzero(abs(pts[2, :]) > np.spacing(1))

    # if len(finiteind) != pts.shape[1]:
    #     print('Some points are at infinity')

    dist = []
    for i in finiteind:
        pts[0, i] = pts[0, i]/pts[2, i]
        pts[1, i] = pts[1, i]/pts[2, i]
        pts[2, i] = 1

        c = np.mean(pts[0:2, i].T, axis=0).T

        newp1 = pts[0, i]-c[0]
        newp2 = pts[1, i]-c[1]

        dist.append(np.sqrt(newp1**2 + newp2**2))

    meandist = np.mean(dist[:])

    scale = np.sqrt(2)/meandist

    T = np.array([[scale, 0, -scale*c[0]], [0, scale, -scale*c[1]], [0, 0, 1]])

    newpts = T.dot(pts)

    return [newpts, T]
