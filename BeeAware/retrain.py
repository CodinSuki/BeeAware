#!/usr/bin/env python3
"""
retrain.py — Retrain the BeeAware classifier using corrections from live sessions.

This script:
1. Loads V3beeware_master_training.csv (original training data)
2. Loads beeaware_corrections.csv (user corrections from live sessions)
3. Merges them on feature_text (adding new labeled examples)
4. Retrains the TfidfVectorizer + LinearSVC with original hyperparameters
5. Saves the new model/vectorizer to models/
6. Archives used corrections to beeaware_corrections_archive.csv
7. Clears beeaware_corrections.csv for the next batch

Usage:
    python retrain.py [--dry-run]  # --dry-run shows what would happen without saving

Hyperparameters (matching V3 training):
    - TfidfVectorizer: ngram_range=(1,2), max_features=12000, stop_words='english'
    - LinearSVC: class_weight='balanced', dual=False, max_iter=10000
"""

import os
import sys
import shutil
import pickle
import argparse
from datetime import datetime
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.svm import LinearSVC


# ============================================================================
# Configuration
# ============================================================================

if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TRAINING_DATA_PATH = os.path.join(BASE_DIR, "Training", "data", "processed", "V3beeware_master_training.csv")
CORRECTIONS_PATH = os.path.join(BASE_DIR, "BeeAware", "data", "beeaware_corrections.csv")
CORRECTIONS_ARCHIVE_PATH = os.path.join(BASE_DIR, "BeeAware", "data", "beeaware_corrections_archive.csv")
MODEL_OUTPUT_PATH = os.path.join(BASE_DIR, "BeeAware", "models", "V4eisenhower_model.pkl")
VECTORIZER_OUTPUT_PATH = os.path.join(BASE_DIR, "BeeAware", "models", "V4tfidf_vectorizer.pkl")
MODEL_BACKUP_PATH = os.path.join(BASE_DIR, "BeeAware", "models", "V4eisenhower_model.backup.pkl")
VECTORIZER_BACKUP_PATH = os.path.join(BASE_DIR, "BeeAware", "models", "V4tfidf_vectorizer.backup.pkl")

# Hyperparameters (matching V3 training)
TFIDF_PARAMS = {
    "ngram_range": (1, 2),
    "max_features": 12000,
    "stop_words": "english",
}
SVC_PARAMS = {
    "class_weight": "balanced",
    "dual": False,
    "max_iter": 10000,
}


# ============================================================================
# Main Logic
# ============================================================================

def load_training_data():
    """Load original training data."""
    if not os.path.exists(TRAINING_DATA_PATH):
        raise FileNotFoundError(f"Training data not found: {TRAINING_DATA_PATH}")
    
    print(f"Loading training data: {TRAINING_DATA_PATH}")
    df = pd.read_csv(TRAINING_DATA_PATH)
    
    # Validate required columns
    required_cols = ["feature_text", "quadrant"]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Training CSV missing required columns: {required_cols}")
    
    print(f"  ✓ Loaded {len(df)} training examples")
    return df[required_cols].copy()


def load_corrections():
    """Load corrections from live sessions.
    
    Returns:
        (corrections_df, num_rows)
    """
    if not os.path.exists(CORRECTIONS_PATH):
        print(f"No corrections file found: {CORRECTIONS_PATH}")
        return None, 0
    
    print(f"Loading corrections: {CORRECTIONS_PATH}")
    df = pd.read_csv(CORRECTIONS_PATH)
    
    if df.empty:
        print("  ⚠ Corrections file is empty")
        return None, 0
    
    # Validate required columns
    required_cols = ["window_title", "feature_text", "predicted_q", "corrected_q"]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"Corrections CSV missing required columns: {required_cols}")
    
    # Map corrected_q (quadrant index 0-3) to quadrant names to match training data
    quadrant_names = {0: "Q1: URGENT", 1: "Q2: GROWTH", 2: "Q3: NOISE", 3: "Q4: PLAY"}
    df["quadrant"] = df["corrected_q"].map(quadrant_names)
    
    result = df[["feature_text", "quadrant"]].copy()
    print(f"  ✓ Loaded {len(result)} corrections")
    return result, len(df)


def merge_training_and_corrections(training_df, corrections_df):
    """Merge training data with corrections.
    
    New corrections override training examples with the same feature_text.
    """
    if corrections_df is None or corrections_df.empty:
        return training_df
    
    print(f"\nMerging training data with corrections...")
    
    # Remove any training examples that are being corrected
    combined = training_df.copy()
    feature_texts_corrected = set(corrections_df["feature_text"])
    before_count = len(combined)
    combined = combined[~combined["feature_text"].isin(feature_texts_corrected)]
    removed = before_count - len(combined)
    
    # Append corrected versions
    combined = pd.concat([combined, corrections_df], ignore_index=True)
    
    print(f"  • Removed {removed} conflicting training examples")
    print(f"  • Added {len(corrections_df)} corrected examples")
    print(f"  ✓ Total examples: {len(combined)}")
    
    return combined


def train_model(training_df):
    """Train TfidfVectorizer + LinearSVC on feature_text and quadrant."""
    print(f"\nTraining model...")
    
    X = training_df["feature_text"].values
    y = training_df["quadrant"].values
    
    # Train vectorizer
    print(f"  • Fitting TfidfVectorizer...")
    vectorizer = TfidfVectorizer(**TFIDF_PARAMS)
    X_tfidf = vectorizer.fit_transform(X)
    print(f"    - Vocabulary size: {len(vectorizer.get_feature_names_out())}")
    
    # Train classifier
    print(f"  • Training LinearSVC...")
    classifier = LinearSVC(**SVC_PARAMS)
    classifier.fit(X_tfidf, y)
    print(f"    - Classes: {classifier.classes_}")
    
    print(f"  ✓ Model trained successfully")
    return vectorizer, classifier


def save_model(vectorizer, classifier, dry_run=False):
    """Save trained model and vectorizer."""
    if dry_run:
        print(f"\n[DRY-RUN] Would save:")
        print(f"  • Model: {MODEL_OUTPUT_PATH}")
        print(f"  • Vectorizer: {VECTORIZER_OUTPUT_PATH}")
        return
    
    print(f"\nSaving model...")
    
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    
    # Backup existing models
    if os.path.exists(MODEL_OUTPUT_PATH):
        shutil.copy(MODEL_OUTPUT_PATH, MODEL_BACKUP_PATH)
        print(f"  • Backed up previous model to: {MODEL_BACKUP_PATH}")
    
    if os.path.exists(VECTORIZER_OUTPUT_PATH):
        shutil.copy(VECTORIZER_OUTPUT_PATH, VECTORIZER_BACKUP_PATH)
        print(f"  • Backed up previous vectorizer to: {VECTORIZER_BACKUP_PATH}")
    
    # Save new models
    with open(MODEL_OUTPUT_PATH, "wb") as f:
        pickle.dump(classifier, f)
    print(f"  ✓ Model saved: {MODEL_OUTPUT_PATH}")
    
    with open(VECTORIZER_OUTPUT_PATH, "wb") as f:
        pickle.dump(vectorizer, f)
    print(f"  ✓ Vectorizer saved: {VECTORIZER_OUTPUT_PATH}")


def archive_corrections(num_corrections, dry_run=False):
    """Archive used corrections and clear the active file."""
    if num_corrections == 0:
        return
    
    if dry_run:
        print(f"\n[DRY-RUN] Would archive {num_corrections} corrections to:")
        print(f"  • {CORRECTIONS_ARCHIVE_PATH}")
        print(f"  • Clear {CORRECTIONS_PATH}")
        return
    
    print(f"\nArchiving corrections...")
    
    os.makedirs(os.path.dirname(CORRECTIONS_ARCHIVE_PATH), exist_ok=True)
    
    # Append to archive with timestamp header
    if os.path.exists(CORRECTIONS_PATH):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Read corrections
        corrections_df = pd.read_csv(CORRECTIONS_PATH)
        
        # Append to archive
        if os.path.exists(CORRECTIONS_ARCHIVE_PATH):
            archive_df = pd.read_csv(CORRECTIONS_ARCHIVE_PATH)
            corrections_df = pd.concat([archive_df, corrections_df], ignore_index=True)
        
        corrections_df.to_csv(CORRECTIONS_ARCHIVE_PATH, index=False)
        print(f"  ✓ Archived to: {CORRECTIONS_ARCHIVE_PATH}")
        
        # Clear active corrections file
        open(CORRECTIONS_PATH, "w").close()
        print(f"  ✓ Cleared: {CORRECTIONS_PATH}")


def main():
    parser = argparse.ArgumentParser(
        description="Retrain BeeAware classifier with live session corrections."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without saving",
    )
    args = parser.parse_args()
    
    try:
        print("=" * 70)
        print("BeeAware Model Retraining")
        print("=" * 70)
        
        # Load data
        training_df = load_training_data()
        corrections_df, num_corrections = load_corrections()
        
        # Check if there are corrections to process
        if num_corrections == 0:
            print("\n✓ No corrections to process. Model unchanged.")
            return 0
        
        # Merge and retrain
        combined_df = merge_training_and_corrections(training_df, corrections_df)
        vectorizer, classifier = train_model(combined_df)
        
        # Save and archive
        save_model(vectorizer, classifier, dry_run=args.dry_run)
        archive_corrections(num_corrections, dry_run=args.dry_run)
        
        if args.dry_run:
            print("\n[DRY-RUN] Retraining simulation complete (no changes made).")
        else:
            print("\n" + "=" * 70)
            print("✓ Retraining complete!")
            print("=" * 70)
        
        return 0
    
    except Exception as e:
        print(f"\n✗ Error during retraining: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
