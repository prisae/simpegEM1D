import scipy as sp
import numpy as np
from SimPEG.Regularization import Sparse, SparseSmall, SparseDeriv
from SimPEG import Mesh, Utils


def get_2d_mesh(n_sounding, hz):
    """
        Generate 2D mesh for regularization

        xy:
        hz:

    """
    hx = np.ones(n_sounding)
    return Mesh.TensorMesh([hz, hx])


class LateralConstraint(Sparse):

    def get_grad_horizontal(self, xy, hz):
        """
            Compute Gradient in horizontal direction using Delaunay

        """
        tri = sp.spatial.Delaunay(xy)
        # Split the triangulation into connections
        edges = np.r_[
            tri.simplices[:, :2],
            tri.simplices[:, 1:],
            tri.simplices[:, [0, 2]]
        ]

        # Sort and keep uniques
        edges = np.sort(edges, axis=1)
        edges = np.unique(
            edges[np.argsort(edges[:, 0]), :], axis=0
        )

        # Create 2D operator, dimensionless for now
        nN = edges.shape[0]
        nStn = xy.shape[0]
        stn, count = np.unique(edges[:, 0], return_counts=True)

        col = []
        row = []
        dm = []
        avg = []
        for ii in range(nN):
            row += [ii]*2
            col += [edges[ii, 0], edges[ii, 1]]

            scale = count[stn == edges[ii, 0]][0]
            dm += [-1., 1.]
            avg += [0.5, 0.5]

        D = sp.sparse.csr_matrix((dm, (row, col)), shape=(nN, nStn))
        A = sp.sparse.csr_matrix((avg, (row, col)), shape=(nN, nStn))

        # Kron vertically for nCz
        Grad = sp.sparse.kron(D, Utils.speye(hz.size))
        Avg = sp.sparse.kron(A, Utils.speye(hz.size))
        # Override the gradient operator in X with the one created above
        self.regmesh._cellDiffyStencil = self.regmesh.cellDiffxStencil.copy()
        self.regmesh._cellDiffxStencil = Grad
        # Do the same for the averaging operator
        self.regmesh._aveCC2Fx = Avg
        return tri
