"""
Utility functions for drowsiness detection using Eye Aspect Ratio (EAR) method.

Reference: Soukupová & Tereza (2016)
"Real-Time Eye Blink Detection using Facial Landmarks"
"""

import numpy as np
from scipy.spatial.distance import euclidean


def compute_eye_aspect_ratio(eye_landmarks):
    """
    Compute the Eye Aspect Ratio (EAR) for an eye given its 6 landmark points.
    
    The EAR is defined as:
    
        EAR = (||p2 - p6|| + ||p3 - p5||) / (2 × ||p1 - p4||)
    
    Where:
    - p1, p4: Horizontal eye corners (left, right)
    - p2, p6: Vertical distances on left and right sides of the eyelid
    - p3, p5: Vertical distances on the eyelid opening
    
    EAR is invariant to head distance and scale, making it robust for
    real-world drowsiness detection.
    
    Parameters
    ----------
    eye_landmarks : np.ndarray or array-like
        Array of shape (6, 2) containing (x, y) coordinates of 6 eye landmark
        points in order: [left_corner, top_left, top_right, right_corner,
        bottom_right, bottom_left].
        
        These correspond to dlib's eye region indices:
        - Left eye: dlib points 36-41
        - Right eye: dlib points 42-47
    
    Returns
    -------
    float
        The computed Eye Aspect Ratio. Typical ranges:
        - Eyes open: ~0.40-0.50
        - Eyes closing: ~0.25-0.35
        - Eyes closed: ~0.10-0.20
    
    Raises
    ------
    ValueError
        If eye_landmarks does not have shape (6, 2)
    
    Examples
    --------
    >>> eye_points = np.array([[10, 20], [12, 15], [18, 15],
    ...                         [20, 20], [18, 25], [12, 25]])
    >>> ear = compute_eye_aspect_ratio(eye_points)
    >>> print(f"EAR: {ear:.3f}")
    """
    # Validate input
    eye_landmarks = np.asarray(eye_landmarks, dtype=np.float32)
    if eye_landmarks.shape != (6, 2):
        raise ValueError(
            f"Expected eye_landmarks shape (6, 2), got {eye_landmarks.shape}"
        )
    
    # Extract landmark points
    p1 = eye_landmarks[0]  # Left corner
    p2 = eye_landmarks[1]  # Top-left
    p3 = eye_landmarks[2]  # Top-right
    p4 = eye_landmarks[3]  # Right corner
    p5 = eye_landmarks[4]  # Bottom-right
    p6 = eye_landmarks[5]  # Bottom-left
    
    # Calculate vertical distances (numerator components)
    # Left vertical: distance between upper and lower eyelid on left side
    vertical_left = euclidean(p2, p6)
    
    # Right vertical: distance between upper and lower eyelid on right side
    vertical_right = euclidean(p3, p5)
    
    # Calculate horizontal distance (denominator: eye width)
    horizontal = euclidean(p1, p4)
    
    # Compute EAR: (sum of vertical distances) / (2 × horizontal distance)
    # The factor of 2 normalizes by the eye width in the denominator
    ear = (vertical_left + vertical_right) / (2.0 * horizontal)
    
    return float(ear)


def validate_landmarks(landmarks):
    """
    Validate that landmarks is a valid array of eye coordinates.
    
    Parameters
    ----------
    landmarks : np.ndarray or array-like
        Expected shape (6, 2) for eye landmarks
    
    Returns
    -------
    bool
        True if valid, False otherwise
    """
    try:
        landmarks = np.asarray(landmarks)
        return landmarks.shape == (6, 2) and landmarks.dtype in (
            np.float32, np.float64, np.int32, np.int64
        )
    except (TypeError, ValueError):
        return False



