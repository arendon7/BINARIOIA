POSITIONS={
    "top-left":"(W-w)*0.04:(H-h)*0.04",
    "top-right":"(W-w)*0.96-w:(H-h)*0.04",
    "bottom-left":"(W-w)*0.04:(H-h)*0.96-h",
    "bottom-right":"(W-w)*0.96-w:(H-h)*0.96-h",
    "center":"(W-w)/2:(H-h)/2"
}

def overlay_xy(position):
    return POSITIONS.get(position, POSITIONS["top-right"])

def overlay_xy_asset(asset):
    if getattr(asset, "x_norm", None) is not None and getattr(asset, "y_norm", None) is not None:
        x = max(0.0, min(1.0, float(asset.x_norm)))
        y = max(0.0, min(1.0, float(asset.y_norm)))
        return f"(W-w)*{x:.6f}:(H-h)*{y:.6f}"
    return overlay_xy(asset.position)
