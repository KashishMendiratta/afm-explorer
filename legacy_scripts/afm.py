from argparse import ArgumentParser
import pickle
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
from scipy.signal import savgol_filter
from scipy.stats import linregress

@st.cache_data
def load_data(prefix):
    print(f"- Loading {prefix}{{.data.pickled,.heights.npy}}")
    hname = f"{prefix}.heights.npy"
    H = np.load(hname)
    m, n = H.shape
    fname = f"{prefix}.data.pickled"
    with open(fname, 'rb') as f:
        data = pickle.load(f)

    # Estimate all slopes
    slope_est = dict()  # maps tuple (s, i, j) to tuple (slope, anchors, info)
    for point, curve in data.items():
        s, i, j = point
        slope_est[point] = estimate_slope(curve, s)
    nseries = 1 + max(s for s, i, j in data.keys())
    slope_heatmaps = []
    for s in range(nseries):
        M = np.array([[(slope_est[s, i, j][0]) for j in range(n)] for i in range(m)], dtype=np.float64)
        slope_heatmaps.append(M)
    return H, data, slope_est, slope_heatmaps

def do_plot(point, curve, slope=None, anchors=None):
    """plot one distance-force curve with estimated slope"""
    s, i, j = point
    d, f = curve
    fig = plt.figure(figsize=[10, 6])
    plt.xlabel("distance (m)")
    plt.ylabel("force (N)")
    mode = 'push' if s == 0 else 'retract'
    plt.title(f"{mode} at ({i}, {j});  number of records: {len(d)}")
    label = f'data: {mode} at {(i, j)}'
    plt.scatter(d, f, s=1, label=label)
    plt.grid()
    if slope is not None and anchors is not None:
        anchor0, anchor1 = anchors[0], anchors[1]
        plt.axline(anchor0, slope=slope, color='red', linestyle='--', label=f'{slope:.4g} N/m')
        plt.plot([anchor0[0]], [anchor0[1]], 'rx')
        plt.plot([anchor1[0]], [anchor1[1]], 'rx')
    plt.legend()
    return fig

def estimate_slope(curve, s, nan=float("nan")):
    d, f = curve
    if s == 0:
        d, f = d[::-1], f[::-1]  # reverse d and f for series-0 spectra !
        # d is now increasing, f (on the left side) is decreasing.
        
    # Apply Savitzky-Golay filter to smooth the data
    f_smooth = savgol_filter(f, window_length=11, polyorder=2)

    # Identify the region of interest
    num_points = len(f_smooth)
    linear_region_end = max(1, int(num_points * 0.1))
    d_linear, f_linear = d[:linear_region_end], f_smooth[:linear_region_end]

    # Perform linear regression on the selected linear region
    slope, intercept, r_value, p_value, std_err = linregress(d_linear, f_linear)

    # Define anchors as the first and last point used for slope estimation
    anchor1 = (d_linear[0], f_linear[0])
    anchor2 = (d_linear[-1], f_linear[-1])
    anchors = (anchor1, anchor2)
    info = {"r_value": r_value, "p_value": p_value, "std_err": std_err}

    return (slope, anchors, info)

# MAIN script

p = ArgumentParser()
p.add_argument("prefix",
    help="common path prefix for spectra (.data.pickled) and heights (.heights.npy)")
args = p.parse_args()
prefix = args.prefix

st.sidebar.title("AFM Data Explorer")
st.sidebar.write(f"Path prefix:\n'{prefix}'")
H, S, slope_est, slope_heatmaps = load_data(prefix)  # cached
m, n = H.shape
nseries = len(slope_heatmaps)

s = st.sidebar.selectbox('Select series', range(nseries))
i = st.sidebar.slider('Select vertical coordinate (i)', 0, m-1, 0)
j = st.sidebar.slider('Select horizontal coordinate (j)', 0, n-1, 0)

st.header('Heights Heatmap')
plt.imshow(H, cmap='turbo')
st.pyplot(plt)

st.header('Slope Heatmap')
plt.imshow(slope_heatmaps[s], cmap='turbo')
st.pyplot(plt)

st.header(f'Measurement at (s={s}, i={i}, j={j})')
point = (s, i, j)
curve = S[point]
slope, anchors, _ = slope_est[point]
fig = do_plot(point, curve, slope, anchors)
st.pyplot(fig)
