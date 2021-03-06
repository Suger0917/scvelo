import numpy as np
from scipy.sparse import issparse


def show_proportions(adata):
    """Fraction of spliced/unspliced/ambiguous abundances

    Arguments
    ---------
    adata: :class:`~anndata.AnnData`
        Annotated data matrix.

    Returns
    -------
    Prints the fractions of abundances.
    """
    layers_keys = [key for key in ['spliced', 'unspliced', 'ambiguous'] if key in adata.layers.keys()]
    tot_mol_cell_layers = [adata.layers[key].sum(1) for key in layers_keys]

    mean_abundances = np.round(
        [np.mean(tot_mol_cell / np.sum(tot_mol_cell_layers, 0)) for tot_mol_cell in tot_mol_cell_layers], 2)

    print('Abundance of ' + str(layers_keys) + ': ' + str(mean_abundances))


def cleanup(data, clean='layers', keep={'spliced', 'unspliced'}, copy=False):
    """Deletes attributes not needed.

    Arguments
    ---------
    data: :class:`~anndata.AnnData`
        Annotated data matrix.
    cleanup: `str` or list of `str` (default: `layers`)
        Which attributes to consider for freeing memory.
    keep: `str` or list of `str` (default: `['spliced', unspliced']`)
        Which attributes to keep.
    copy: `bool` (default: `False`)
        Return a copy instead of writing to adata.

    Returns
    -------
    Returns or updates `adata` with selection of attributes kept.
    """
    adata = data.copy() if copy else data

    if any(['obs' in clean, 'all' in clean]):
        for key in list(adata.obs.keys()):
            if key not in keep: del adata.obs[key]

    if any(['var' in clean, 'all' in clean]):
        for key in list(adata.var.keys()):
            if key not in keep: del adata.var[key]

    if any(['uns' in clean, 'all' in clean]):
        for key in list(adata.uns.keys()):
            if key not in keep: del adata.uns[key]

    if any(['layers' in clean, 'all' in clean]):
        for key in list(adata.layers.keys()):  # remove layers that are not needed
            if key not in keep: del adata.layers[key]

    return adata if copy else None


def filter_and_normalize(data, min_counts=3, min_counts_u=3, min_cells=None, min_cells_u=None, n_top_genes=None,
                         log=True, plot=False, copy=False):
    """Filtering, normalization and log transform

    Expects non-logarithmized data. If using logarithmized data, pass `log=False`.

    Runs the following steps

    .. code:: python

        sc.pp.filter_genes(adata, min_counts=10)
        sc.pp.normalize_per_cell(adata)
        sc.pp.filter_genes_dispersion(adata, n_top_genes=10000)
        sc.pp.normalize_per_cell(adata)
        if log: sc.pp.log1p(adata)


    Arguments
    ---------
    data: :class:`~anndata.AnnData`
        Annotated data matrix.
    min_counts: `int` (default: 10)
        Minimum number of gene counts per cell.
    n_top_genes: `int` (default: 10000)
        Number of genes to keep.
    log: `bool` (default: `True`)
        Take logarithm.
    copy: `bool` (default: `False`)
        Return a copy of `adata` instead of updating it.

    Returns
    -------
    Returns or updates `adata` depending on `copy`.
    """
    adata = data.copy() if copy else data
    from scanpy.api.pp import filter_genes, filter_genes_dispersion, normalize_per_cell, log1p

    def filter_genes_u(adata, min_counts_u=None, min_cells_u=None):
        counts = adata.layers['unspliced'] if min_counts_u is not None else adata.layers['unspliced'] > 0
        counts = counts.sum(0).A1 if issparse(counts) else counts.sum(0)
        adata._inplace_subset_var(counts >= (min_counts_u if min_counts_u is not None else min_cells_u))

    if min_counts is not None: filter_genes(adata, min_counts=min_counts)
    if min_cells is not None: filter_genes(adata, min_cells=min_cells)

    if 'unspliced' in adata.layers.keys():
        if min_counts_u is not None: filter_genes_u(adata, min_counts_u=min_counts_u)
        if min_cells_u is not None: filter_genes_u(adata, min_cells_u=min_cells_u)

    if n_top_genes is not None and n_top_genes < adata.shape[1]:
        normalize_per_cell(adata)

        filter_result = filter_genes_dispersion(adata.X, n_top_genes=n_top_genes, log=False)
        if plot:
            from scanpy.plotting.preprocessing import filter_genes_dispersion as plot_filter_genes_dispersion
            plot_filter_genes_dispersion(filter_result, log=True)
        adata._inplace_subset_var(filter_result.gene_subset)

        #filter_genes_dispersion(adata, n_top_genes=n_top_genes)

    normalize_per_cell(adata)
    if log: log1p(adata)
    return adata if copy else None


def recipe_velocity(adata, min_counts=3, min_counts_u=3, n_top_genes=None, n_pcs=30, n_neighbors=30, log=True, copy=False):
    """Runs pp.filter_and_normalize() and pp.moments()
    """
    from .moments import moments
    filter_and_normalize(adata, min_counts=min_counts, min_counts_u=min_counts_u, n_top_genes=n_top_genes, log=log)
    moments(adata, n_neighbors=n_neighbors, n_pcs=n_pcs)
    return adata if copy else None
