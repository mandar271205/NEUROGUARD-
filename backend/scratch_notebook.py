# librosa          → audio feature extraction
# shap             → model explainability
# imbalanced-learn → handle class imbalance with SMOTE
!pip install -q librosa shap imbalanced-learn
print('✅ All packages installed successfully!')

# CELL 

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import warnings
import zipfile
import os
import glob
import librosa
import shap
import joblib
warnings.filterwarnings('ignore')

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.metrics import (
    accuracy_score, classification_report,
    confusion_matrix, roc_auc_score, f1_score
)
from imblearn.over_sampling import SMOTE

import tensorflow as tf
from tensorflow.keras.models import Sequential, Model
from tensorflow.keras.layers import (
    LSTM, Dense, Dropout, BatchNormalization, Input
)
from tensorflow.keras.callbacks import EarlyStopping
from tensorflow.keras.utils import to_categorical

print(f'✅ TensorFlow  : {tf.__version__}')
print(f'✅ GPU available: {len(tf.config.list_physical_devices("GPU")) > 0}')
print('✅ All libraries imported!')

# CELL 

df = pd.read_csv('StressLevelDataset.csv')

print('=== Dataset Overview ===')
print(f'Rows    : {df.shape[0]}')
print(f'Columns : {df.shape[1]}')

print('\n=== Stress Level Distribution ===')
counts = df['stress_level'].value_counts().sort_index()
labels = ['0 = Normal', '1 = High Stress', '2 = High Risk']
for i, count in enumerate(counts.values):
    print(f'  {labels[i]}: {count} students ({count / len(df) * 100:.1f}%)')

print('\n=== Column Names ===')
print(df.columns.tolist())

print('\n=== First 3 Rows ===')
df.head(3)

# CELL 

fig, axes = plt.subplots(2, 3, figsize=(18, 11))
fig.suptitle('NeuroGuard — Data Analysis Dashboard',
             fontsize=18, fontweight='bold', y=1.01)

COLORS = ['#2ecc71', '#f39c12', '#e74c3c']  # Normal / High-Stress / High-Risk
CLASS_LABELS = ['Normal (0)', 'High-Stress (1)', 'High-Risk (2)']

# 1 ── Class distribution bar chart
counts = df['stress_level'].value_counts().sort_index()
bars = axes[0, 0].bar(CLASS_LABELS, counts.values,
                       color=COLORS, edgecolor='black', width=0.5)
axes[0, 0].set_title('Students per Stress Class', fontweight='bold')
axes[0, 0].set_ylabel('Number of Students')
for bar, val in zip(bars, counts.values):
    axes[0, 0].text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 5,
                    str(val), ha='center', fontweight='bold', fontsize=12)

# 2 ── Anxiety level histogram by class
for i, label in enumerate([0, 1, 2]):
    axes[0, 1].hist(df[df['stress_level'] == label]['anxiety_level'],
                    alpha=0.6, label=CLASS_LABELS[i], bins=15, color=COLORS[i])
axes[0, 1].set_title('Anxiety Level by Stress Class', fontweight='bold')
axes[0, 1].set_xlabel('Anxiety Level')
axes[0, 1].set_ylabel('Count')
axes[0, 1].legend()

# 3 ── Sleep quality histogram by class
for i, label in enumerate([0, 1, 2]):
    axes[0, 2].hist(df[df['stress_level'] == label]['sleep_quality'],
                    alpha=0.6, label=CLASS_LABELS[i], bins=6, color=COLORS[i])
axes[0, 2].set_title('Sleep Quality by Stress Class', fontweight='bold')
axes[0, 2].set_xlabel('Sleep Quality')
axes[0, 2].set_ylabel('Count')
axes[0, 2].legend()

# 4 ── Correlation heatmap
top_features = [
    'anxiety_level', 'self_esteem', 'depression', 'sleep_quality',
    'academic_performance', 'social_support', 'stress_level'
]
sns.heatmap(df[top_features].corr(), ax=axes[1, 0], cmap='coolwarm',
            annot=True, fmt='.2f', linewidths=0.5)
axes[1, 0].set_title('Feature Correlation Heatmap', fontweight='bold')

# 5 ── Self-esteem vs depression scatter
for i, label in enumerate([0, 1, 2]):
    mask = df['stress_level'] == label
    axes[1, 1].scatter(df[mask]['self_esteem'], df[mask]['depression'],
                       c=COLORS[i], alpha=0.5, label=CLASS_LABELS[i], s=40)
axes[1, 1].set_title('Self-Esteem vs Depression', fontweight='bold')
axes[1, 1].set_xlabel('Self-Esteem (higher = better)')
axes[1, 1].set_ylabel('Depression Level')
axes[1, 1].legend()

# 6 ── Average feature values by class
key_feats = ['anxiety_level', 'depression', 'study_load', 'sleep_quality']
class_means = df.groupby('stress_level')[key_feats].mean()
class_means.T.plot(kind='bar', ax=axes[1, 2], color=COLORS, edgecolor='black')
axes[1, 2].set_title('Average Feature Values by Stress Class', fontweight='bold')
axes[1, 2].set_xticklabels(key_feats, rotation=15)
axes[1, 2].legend(CLASS_LABELS)
axes[1, 2].set_ylabel('Average Value')

plt.tight_layout()
plt.savefig('eda_dashboard.png', dpi=150, bbox_inches='tight')
plt.show()
print('✅ EDA complete — saved as eda_dashboard.png')

# CELL 

df_fe = df.copy()

# ── Composite feature 1: Overall Risk Score
df_fe['risk_score'] = (
    df_fe['anxiety_level']        * 0.30 +
    df_fe['depression']           * 0.30 +
    (30 - df_fe['self_esteem'])   * 0.20 +  # inverted: lower self-esteem → higher risk
    (5  - df_fe['sleep_quality']) * 0.10 +  # inverted: worse sleep → higher risk
    df_fe['study_load']           * 0.10
)

# ── Composite feature 2: Social Isolation Index
df_fe['social_isolation'] = (
    (3 - df_fe['social_support']) + df_fe['peer_pressure']
) / 2

# ── Composite feature 3: Environmental Stress
df_fe['env_stress'] = (
    df_fe['noise_level'] +
    (5 - df_fe['living_conditions']) +
    (5 - df_fe['safety']) +
    (5 - df_fe['basic_needs'])
) / 4

feature_cols = [c for c in df_fe.columns if c != 'stress_level']
X = df_fe[feature_cols].values
y = df_fe['stress_level'].values

print(f'Total features : {len(feature_cols)}')
print(f'New features   : risk_score, social_isolation, env_stress')
print(f'X shape        : {X.shape}')
print(f'y shape        : {y.shape}')
print(f'Class counts   : Normal={sum(y==0)}, High-Stress={sum(y==1)}, High-Risk={sum(y==2)}')

# CELL 

indices = np.arange(len(X))

X_train, X_test, y_train, y_test, idx_train, idx_test = train_test_split(
    X, y, indices,
    test_size=0.2,
    random_state=42,
    stratify=y
)

scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled  = scaler.transform(X_test)

# Apply SMOTE only if classes are imbalanced (>20% gap)
class_counts = np.bincount(y_train)
if min(class_counts) < max(class_counts) * 0.8:
    smote = SMOTE(random_state=42)
    X_train_scaled, y_train = smote.fit_resample(X_train_scaled, y_train)
    print(f'✅ SMOTE applied — new class counts: {np.bincount(y_train)}')
else:
    print(f'✅ Classes balanced — SMOTE not needed: {class_counts}')

print(f'\nTrain samples : {X_train_scaled.shape[0]}')
print(f'Test  samples : {X_test_scaled.shape[0]}')
print(f'Features      : {X_train_scaled.shape[1]}')

# CELL 

print('Training Logistic Regression...')

lr = LogisticRegression(
    max_iter=1000, C=1.0,
    random_state=42, multi_class='multinomial'
)
lr.fit(X_train_scaled, y_train)

lr_preds = lr.predict(X_test_scaled)
lr_probs = lr.predict_proba(X_test_scaled)

lr_acc = accuracy_score(y_test, lr_preds)
lr_f1  = f1_score(y_test, lr_preds, average='macro')
lr_auc = roc_auc_score(y_test, lr_probs, multi_class='ovr', average='macro')

print(f'\n=== Logistic Regression ===')
print(f'  Accuracy : {lr_acc:.4f}  ({lr_acc*100:.1f}%)')
print(f'  F1 Score : {lr_f1:.4f}')
print(f'  ROC-AUC  : {lr_auc:.4f}')
print()
print(classification_report(y_test, lr_preds,
      target_names=['Normal', 'High-Stress', 'High-Risk']))

cm = confusion_matrix(y_test, lr_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=['Normal', 'High-Stress', 'High-Risk'],
            yticklabels=['Normal', 'High-Stress', 'High-Risk'])
plt.title('Logistic Regression — Confusion Matrix\n(rows=actual, cols=predicted)',
          fontweight='bold')
plt.ylabel('Actual')
plt.xlabel('Predicted')
plt.tight_layout()
plt.show()

lr_result = {'model': 'Logistic Regression', 'accuracy': lr_acc, 'f1': lr_f1, 'auc': lr_auc}
print('✅ Done!')

# CELL 

print('Training Random Forest (200 trees)...')

rf = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=-1)
rf.fit(X_train_scaled, y_train)

rf_preds = rf.predict(X_test_scaled)
rf_probs = rf.predict_proba(X_test_scaled)

rf_acc = accuracy_score(y_test, rf_preds)
rf_f1  = f1_score(y_test, rf_preds, average='macro')
rf_auc = roc_auc_score(y_test, rf_probs, multi_class='ovr', average='macro')

print(f'\n=== Random Forest ===')
print(f'  Accuracy : {rf_acc:.4f}  ({rf_acc*100:.1f}%)')
print(f'  F1 Score : {rf_f1:.4f}')
print(f'  ROC-AUC  : {rf_auc:.4f}')
print()
print(classification_report(y_test, rf_preds,
      target_names=['Normal', 'High-Stress', 'High-Risk']))

cm = confusion_matrix(y_test, rf_preds)
plt.figure(figsize=(6, 5))
sns.heatmap(cm, annot=True, fmt='d', cmap='Greens',
            xticklabels=['Normal', 'High-Stress', 'High-Risk'],
            yticklabels=['Normal', 'High-Stress', 'High-Risk'])
plt.title('Random Forest — Confusion Matrix', fontweight='bold')
plt.ylabel('Actual')
plt.xlabel('Predicted')
plt.tight_layout()
plt.show()

rf_result = {'model': 'Random Forest', 'accuracy': rf_acc, 'f1': rf_f1, 'auc': rf_auc}
print('✅ Done!')

# CELL 

SEQ_LEN   = 8
N_FEAT    = X_train_scaled.shape[1]
N_CLASSES = 3


def make_sequences(X, y, seq_len=8, noise=0.15):
    """Expand each sample into a short noisy sequence to simulate time-series."""
    seqs, labels = [], []
    for i in range(len(X)):
        seq = np.array([
            X[i] + np.random.normal(0, noise * t, X.shape[1])
            for t in np.linspace(0.1, 1.0, seq_len)
        ])
        seqs.append(seq)
        labels.append(y[i])
    return np.array(seqs), np.array(labels)


print('Creating sequences...')
X_seq_train, y_seq_train = make_sequences(X_train_scaled, y_train, SEQ_LEN)
X_seq_test,  y_seq_test  = make_sequences(X_test_scaled,  y_test,  SEQ_LEN)

y_seq_train_cat = to_categorical(y_seq_train, N_CLASSES)
y_seq_test_cat  = to_categorical(y_seq_test,  N_CLASSES)

print(f'Train sequences : {X_seq_train.shape}  (samples, steps, features)')
print(f'Test  sequences : {X_seq_test.shape}')

# ── Build LSTM model
inp = Input(shape=(SEQ_LEN, N_FEAT))
x   = LSTM(128, return_sequences=True)(inp)
x   = Dropout(0.3)(x)
x   = LSTM(64)(x)
x   = Dropout(0.3)(x)
x   = Dense(64, activation='relu')(x)
x   = BatchNormalization()(x)
out = Dense(N_CLASSES, activation='softmax')(x)

lstm_model = Model(inp, out)
lstm_model.compile(
    optimizer='adam',
    loss='categorical_crossentropy',
    metrics=['accuracy']
)
lstm_model.summary()

print('\nTraining LSTM (up to 80 epochs, early stopping patience=10)...')
history = lstm_model.fit(
    X_seq_train, y_seq_train_cat,
    epochs=80, batch_size=32,
    validation_data=(X_seq_test, y_seq_test_cat),
    callbacks=[EarlyStopping(patience=10, restore_best_weights=True)],
    verbose=1
)

lstm_probs = lstm_model.predict(X_seq_test)
lstm_preds = np.argmax(lstm_probs, axis=1)

lstm_acc = accuracy_score(y_seq_test, lstm_preds)
lstm_f1  = f1_score(y_seq_test, lstm_preds, average='macro')
lstm_auc = roc_auc_score(y_seq_test_cat, lstm_probs, multi_class='ovr', average='macro')

print(f'\n=== LSTM ===')
print(f'  Accuracy : {lstm_acc:.4f}  ({lstm_acc*100:.1f}%)')
print(f'  F1 Score : {lstm_f1:.4f}')
print(f'  ROC-AUC  : {lstm_auc:.4f}')

lstm_result = {'model': 'LSTM', 'accuracy': lstm_acc, 'f1': lstm_f1, 'auc': lstm_auc}

# ── Training curves
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
ax1.plot(history.history['loss'],     label='Train')
ax1.plot(history.history['val_loss'], label='Val')
ax1.set_title('Loss'); ax1.legend()
ax2.plot(history.history['accuracy'],     label='Train')
ax2.plot(history.history['val_accuracy'], label='Val')
ax2.set_title('Accuracy'); ax2.legend()
plt.tight_layout()
plt.show()
print('✅ LSTM done!')

# CELL 

import os
import zipfile
import glob
import numpy as np
import librosa

zip_path = 'audio_speech_actors_01-24.zip'

# ── Step 1: Validate and Unzip
if not os.path.exists(zip_path):
    print(f'❌ ERROR: {zip_path} not found. Please upload it.')
else:
    if not os.path.exists('ravdess'):
        print('Unzipping audio files...')
        !unzip -q {zip_path} -d ravdess

    wav_files = glob.glob('ravdess/**/*.wav', recursive=True)
    print(f'✅ Found {len(wav_files)} WAV files')

# ── Step 2: Extraction Function
def extract_audio_features(path):
    try:
        y, sr = librosa.load(path, sr=22050)
        mfccs = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=40)
        mfcc_mean, mfcc_std = np.mean(mfccs, axis=1), np.std(mfccs, axis=1)
        chroma = np.mean(librosa.feature.chroma_stft(y=y, sr=sr), axis=1)
        mel = np.mean(librosa.feature.melspectrogram(y=y, sr=sr), axis=1)[:20]
        contrast = np.mean(librosa.feature.spectral_contrast(y=y, sr=sr), axis=1)

        f0, _, _ = librosa.pyin(y, fmin=50, fmax=400)
        f0_clean = f0[~np.isnan(f0)] if f0 is not None and len(f0[~np.isnan(f0)]) > 0 else np.array([0.0])
        pitch_mean, pitch_std = np.mean(f0_clean), np.std(f0_clean)

        rms = librosa.feature.rms(y=y)[0]
        shimmer = np.std(rms) / (np.mean(rms) + 1e-8)
        zcr = np.mean(librosa.feature.zero_crossing_rate(y)[0])
        centroid = np.mean(librosa.feature.spectral_centroid(y=y, sr=sr))

        return np.concatenate([mfcc_mean, mfcc_std, chroma, mel, contrast, [pitch_mean, pitch_std, shimmer, zcr, centroid]])
    except:
        return None

# ── Step 3: Process Files into X_audio and y_audio
EMOTION_TO_STRESS = {'01':0, '02':0, '03':0, '04':1, '08':1, '05':2, '06':2, '07':2}
audio_features, audio_labels = [], []

print('Extracting features (this takes 5-10 mins)...')
for i, path in enumerate(wav_files):
    if i % 200 == 0: print(f'  Progress: {i}/{len(wav_files)}')
    fname = os.path.basename(path)
    parts = fname.split('-')
    if len(parts) >= 3:
        emotion = parts[2]
        if emotion in EMOTION_TO_STRESS:
            feats = extract_audio_features(path)
            if feats is not None:
                audio_features.append(feats)
                audio_labels.append(EMOTION_TO_STRESS[emotion])

X_audio = np.array(audio_features)
y_audio = np.array(audio_labels)
print(f'✅ Done! Shape: {X_audio.shape}')

# CELL 

AUDIO_FEATURES = 124  # updated from 85

X_au_tr, X_au_te, y_au_tr, y_au_te = train_test_split(
    X_audio, y_audio, test_size=0.2, random_state=42, stratify=y_audio
)

au_scaler  = StandardScaler()
X_au_tr_sc = au_scaler.fit_transform(X_au_tr)
X_au_te_sc = au_scaler.transform(X_au_te)

# IMPROVED: deeper network (256→256→128→64) vs original (256→128→64)
audio_model = Sequential([
    Input(shape=(AUDIO_FEATURES,)),

    Dense(256, activation='relu'),
    BatchNormalization(), Dropout(0.3),

    Dense(256, activation='relu'),      # NEW extra layer
    BatchNormalization(), Dropout(0.3),

    Dense(128, activation='relu'),
    BatchNormalization(), Dropout(0.25),

    Dense(64,  activation='relu'),
    Dropout(0.2),

    Dense(3, activation='softmax')
])

# IMPROVED: lower learning rate (0.001 → 0.0005) for smoother convergence
audio_model.compile(
    optimizer=tf.keras.optimizers.Adam(learning_rate=0.0005),
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# IMPROVED: ReduceLROnPlateau — halves LR when stuck
lr_reducer = tf.keras.callbacks.ReduceLROnPlateau(
    monitor='val_loss', factor=0.5,
    patience=5, min_lr=1e-6, verbose=1
)

print('Training improved audio MLP model...')
audio_model.fit(
    X_au_tr_sc, y_au_tr,
    validation_data=(X_au_te_sc, y_au_te),
    epochs=100,          # IMPROVED: 60 → 100 (early stopping still protects)
    batch_size=32,
    callbacks=[
        EarlyStopping(patience=15, restore_best_weights=True),  # patience 10→15
        lr_reducer                                                  # NEW
    ],
    verbose=1
)

au_preds = np.argmax(audio_model.predict(X_au_te_sc), axis=1)
au_probs = audio_model.predict(X_au_te_sc)

au_acc = accuracy_score(y_au_te, au_preds)
au_f1  = f1_score(y_au_te, au_preds, average='macro')

print(f'\n=== Improved Audio MLP ===')
print(f'  Accuracy : {au_acc:.4f}  ({au_acc*100:.1f}%)')
print(f'  F1 Score : {au_f1:.4f}')
print(classification_report(y_au_te, au_preds,
      target_names=['Normal', 'High-Stress', 'High-Risk']))

audio_result = {'model': 'Audio MLP', 'accuracy': au_acc, 'f1': au_f1, 'auc': 0}
print('✅ Improved audio model trained!')

# CELL 

def simulate_audio_for_student(stress_level):
    """
    Synthesize realistic voice features for a student (now 124 features).
    Higher stress → higher pitch, more tremor, more spectral energy.
    """
    noise      = [0.10, 0.50, 1.00][stress_level]
    pitch_base = [180,  210,  250 ][stress_level]

    # MFCCs — 80 features (unchanged)
    mfcc_mean = np.random.normal(-5 * (stress_level + 1), 5 + noise * 3, 40)
    mfcc_std  = np.random.normal(2 + stress_level, 1 + noise, 40)

    # NEW: Chroma — 12 features (pitch energy varies with stress)
    chroma = np.random.normal(
        0.4 + stress_level * 0.1,   # higher stress → more tonal energy
        0.1 + noise * 0.05,
        12
    )

    # NEW: Mel bands — 20 features (energy distribution shifts with stress)
    mel = np.random.normal(
        5.0 + stress_level * 2.0,   # stressed voices have more high-freq energy
        1.5 + noise,
        20
    )

    # NEW: Spectral contrast — 7 features (stressed voices show more contrast)
    contrast = np.random.normal(
        20.0 + stress_level * 5.0,
        3.0  + noise * 2.0,
        7
    )

    # Pitch, shimmer, ZCR, centroid — 5 features (unchanged)
    extra = np.array([
        pitch_base + np.random.normal(0, 10 + stress_level * 15),
        10 + stress_level * 5  + np.random.normal(0, 3),
        0.01 + stress_level * 0.02 + np.random.normal(0, 0.005),
        0.05 + stress_level * 0.03 + np.random.normal(0, 0.01),
        2000 + stress_level * 300  + np.random.normal(0, 100)
    ])

    return np.concatenate([mfcc_mean, mfcc_std, chroma, mel, contrast, extra])  # 124


np.random.seed(42)
X_audio_synth    = np.array([simulate_audio_for_student(s)
                              for s in df_fe['stress_level']])
X_audio_synth_sc = au_scaler.transform(X_audio_synth)

# Quick shape check — should print (1100, 124)
print(f'✅ Synth audio shape: {X_audio_synth.shape}')

audio_probs_all   = audio_model.predict(X_audio_synth_sc)
audio_probs_train = audio_probs_all[idx_train]
audio_probs_test  = audio_probs_all[idx_test]

tab_probs_train = rf.predict_proba(X_train_scaled)
tab_probs_test  = rf.predict_proba(X_test_scaled)

# Concatenate: [3 survey probs | 3 audio probs] = 6 meta-features
X_fusion_train = np.hstack([tab_probs_train, audio_probs_train])
X_fusion_test  = np.hstack([tab_probs_test,  audio_probs_test])

print(f'Fusion feature shape: {X_fusion_train.shape}  (6 = 3 tabular + 3 audio)')

meta_clf = GradientBoostingClassifier(
    n_estimators=100, learning_rate=0.1,
    max_depth=4, random_state=42
)
meta_clf.fit(X_fusion_train, y_train)

fusion_preds = meta_clf.predict(X_fusion_test)
fusion_probs = meta_clf.predict_proba(X_fusion_test)

fusion_acc = accuracy_score(y_test, fusion_preds)
fusion_f1  = f1_score(y_test, fusion_preds, average='macro')
fusion_auc = roc_auc_score(
    to_categorical(y_test, 3), fusion_probs,
    multi_class='ovr', average='macro'
)

print(f'\n=== Late Fusion (Survey + Voice) ===')
print(f'  Accuracy : {fusion_acc:.4f}  ({fusion_acc*100:.1f}%)')
print(f'  F1 Score : {fusion_f1:.4f}')
print(f'  ROC-AUC  : {fusion_auc:.4f}')
print(classification_report(y_test, fusion_preds,
      target_names=['Normal', 'High-Stress', 'High-Risk']))

fusion_result = {
    'model': 'Late Fusion (Survey+Voice)',
    'accuracy': fusion_acc, 'f1': fusion_f1, 'auc': fusion_auc
}
print('✅ Late Fusion done!')

# CELL 

import matplotlib.pyplot as plt
import shap
import numpy as np

# Standard Colab inline backend is usually 'module://ipykernel.pylab.backend_inline'
%matplotlib inline

print('Re-attempting SHAP rendering with standard backend and explicit figure handling...')

try:
    # Initialize JS for SHAP (helpful for some plot types)
    shap.initjs()

    # Use a small sample
    X_small = X_test_scaled[:50]
    explainer = shap.TreeExplainer(rf)
    # Get Explanation object which works better with modern SHAP plots
    shap_values_obj = explainer(X_small)

    # 1. Beeswarm Plot for High Risk (Class 2)
    plt.figure(figsize=(10, 6))
    # shap_values_obj[:,:,2] selects class 2
    shap.summary_plot(shap_values_obj.values[:,:,2], X_small, feature_names=feature_cols, show=False)
    plt.title('SHAP Drivers for High Risk (Class 2)')
    plt.gcf().set_facecolor('white')
    plt.tight_layout()
    plt.show()
    plt.savefig('shap_high_risk_fix.png')

    # 2. Bar Plot
    plt.figure(figsize=(10, 6))
    shap.summary_plot(shap_values_obj.values[:,:,2], X_small, feature_names=feature_cols, plot_type='bar', show=False)
    plt.title('Feature Importance for High Risk')
    plt.gcf().set_facecolor('white')
    plt.tight_layout()
    plt.show()
    plt.savefig('shap_feature_importance_fix.png')

    print('✅ If graphs appear above, the rendering issue is resolved!')
except Exception as e:
    print(f'❌ Error during re-rendering: {e}')

# CELL 

all_results = [lr_result, rf_result, lstm_result, audio_result, fusion_result]
results_df  = pd.DataFrame(all_results).round(4)

print('=== Final Model Comparison ===')
print(results_df.to_string(index=False))

best_model = results_df.loc[results_df['accuracy'].idxmax(), 'model']
best_acc   = results_df['accuracy'].max()
print(f'\n🏆 Best model: {best_model}  →  {best_acc*100:.1f}% accuracy')

fig, ax = plt.subplots(figsize=(12, 6))
x, w   = np.arange(len(results_df)), 0.25

bars1 = ax.bar(x - w, results_df['accuracy'], w, label='Accuracy',  color='#3498db', edgecolor='black')
bars2 = ax.bar(x,     results_df['f1'],       w, label='F1 Score',  color='#2ecc71', edgecolor='black')
bars3 = ax.bar(x + w, results_df['auc'],      w, label='ROC-AUC',   color='#e74c3c', edgecolor='black')

for bars in [bars1, bars2, bars3]:
    for bar in bars:
        h = bar.get_height()
        if h > 0:
            ax.text(bar.get_x() + bar.get_width() / 2, h + 0.005,
                    f'{h:.3f}', ha='center', va='bottom', fontsize=8)

ax.set_xlabel('Model', fontsize=12)
ax.set_ylabel('Score', fontsize=12)
ax.set_title('NeuroGuard — Model Performance Comparison',
             fontsize=14, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(results_df['model'], rotation=15, ha='right')
ax.set_ylim(0, 1.08)
ax.legend(fontsize=11)
ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig('model_comparison.png', dpi=150, bbox_inches='tight')
plt.show()
print('✅ Saved as model_comparison.png')

# CELL 

import json

# sklearn / meta models
joblib.dump(rf,        'neuroguard_rf.pkl')
joblib.dump(meta_clf,  'neuroguard_fusion.pkl')
joblib.dump(scaler,    'neuroguard_scaler.pkl')
joblib.dump(au_scaler, 'neuroguard_audio_scaler.pkl')

# Keras models
lstm_model.save('neuroguard_lstm.keras')
audio_model.save('neuroguard_audio.keras')

# Feature column names (needed for inference)
with open('neuroguard_features.json', 'w') as f:
    json.dump(feature_cols, f)

SAVED_FILES = [
    'neuroguard_rf.pkl', 'neuroguard_fusion.pkl',
    'neuroguard_scaler.pkl', 'neuroguard_audio_scaler.pkl',
    'neuroguard_lstm.keras', 'neuroguard_audio.keras',
    'neuroguard_features.json'
]

print('✅ All models saved!')
print()
for fname in SAVED_FILES:
    size_kb = os.path.getsize(fname) / 1024
    print(f'  {fname:40s}  ({size_kb:7.1f} KB)')

# CELL 

from google.colab import files

DOWNLOAD_FILES = [
    'neuroguard_rf.pkl',
    'neuroguard_fusion.pkl',
    'neuroguard_scaler.pkl',
    'neuroguard_audio_scaler.pkl',
    'neuroguard_features.json',
    'eda_dashboard.png',
    'model_comparison.png',
    'shap_high_risk.png',
    'shap_feature_importance.png',
]

print('Downloading files...')
for fname in DOWNLOAD_FILES:
    if os.path.exists(fname):
        files.download(fname)
        print(f'  ✅ {fname}')
    else:
        print(f'  ⚠️  {fname} not found — skipping')

print('\nDownloading Keras models (larger files)...')
files.download('neuroguard_lstm.keras')
files.download('neuroguard_audio.keras')
print('\n🎉 All downloads complete!')

# CELL 

# ── Test Case: Normal (Low Stress) ───────────────────────────────────
test_student = {
    'anxiety_level'               : 1,
    'self_esteem'                 : 9,
    'mental_health_history'       : 0,
    'depression'                  : 1,
    'headache'                    : 1,
    'blood_pressure'              : 5,
    'sleep_quality'               : 9,
    'breathing_problem'           : 1,
    'noise_level'                 : 2,
    'living_conditions'           : 9,
    'safety'                      : 9,
    'basic_needs'                 : 9,
    'academic_performance'        : 8,
    'study_load'                  : 3,
    'teacher_student_relationship': 8,
    'future_career_concerns'      : 2,
    'social_support'              : 9,
    'peer_pressure'               : 2,
    'extracurricular_activities'  : 8,
    'bullying'                    : 0,
}

# ── Feature Engineering ─────────────────────────────────────────────
test_student['risk_score'] = (
    test_student['anxiety_level']        * 0.30 +
    test_student['depression']           * 0.30 +
    (30 - test_student['self_esteem'])   * 0.20 +
    (5  - test_student['sleep_quality']) * 0.10 +
    test_student['study_load']           * 0.10
)

test_student['social_isolation'] = (
    (3 - test_student['social_support']) + test_student['peer_pressure']
) / 2

test_student['env_stress'] = (
    test_student['noise_level'] +
    (5 - test_student['living_conditions']) +
    (5 - test_student['safety']) +
    (5 - test_student['basic_needs'])
) / 4

# ── Prediction ──────────────────────────────────────────────────────
test_array  = np.array([[test_student[f] for f in feature_cols]])
test_scaled = scaler.transform(test_array)

pred_class  = rf.predict(test_scaled)[0]
pred_proba  = rf.predict_proba(test_scaled)[0]

CLASS_NAMES  = ['Normal', 'High Stress', 'High Risk']
CLASS_ICONS  = ['🟢', '🟡', '🔴']

print('=== Student Stress Prediction ===')
print(f'  Result     : {CLASS_ICONS[pred_class]} {CLASS_NAMES[pred_class]}')
print(f'  Confidence : {pred_proba[pred_class]*100:.1f}%')
print()

print('  Class probabilities:')
for i, (name, prob) in enumerate(zip(CLASS_NAMES, pred_proba)):
    bar = '█' * int(prob * 30)
    print(f'    {CLASS_ICONS[i]} {name:12s} : {bar:<30s} {prob*100:.1f}%')

# CELL 

# ── Test Case: High Risk (High Stress) ──────────────────────────────
test_student = {
    'anxiety_level'               : 9,
    'self_esteem'                 : 2,
    'mental_health_history'       : 1,
    'depression'                  : 9,
    'headache'                    : 8,
    'blood_pressure'              : 8,
    'sleep_quality'               : 2,
    'breathing_problem'           : 6,
    'noise_level'                 : 8,
    'living_conditions'           : 3,
    'safety'                      : 2,
    'basic_needs'                 : 3,
    'academic_performance'        : 3,
    'study_load'                  : 9,
    'teacher_student_relationship': 3,
    'future_career_concerns'      : 9,
    'social_support'              : 2,
    'peer_pressure'               : 9,
    'extracurricular_activities'  : 1,
    'bullying'                    : 7,
}

# ── Feature Engineering ─────────────────────────────────────────────
test_student['risk_score'] = (
    test_student['anxiety_level']        * 0.30 +
    test_student['depression']           * 0.30 +
    (30 - test_student['self_esteem'])   * 0.20 +
    (5  - test_student['sleep_quality']) * 0.10 +
    test_student['study_load']           * 0.10
)

test_student['social_isolation'] = (
    (3 - test_student['social_support']) + test_student['peer_pressure']
) / 2

test_student['env_stress'] = (
    test_student['noise_level'] +
    (5 - test_student['living_conditions']) +
    (5 - test_student['safety']) +
    (5 - test_student['basic_needs'])
) / 4

# ── Prediction ──────────────────────────────────────────────────────
test_array  = np.array([[test_student[f] for f in feature_cols]])
test_scaled = scaler.transform(test_array)

pred_class  = rf.predict(test_scaled)[0]
pred_proba  = rf.predict_proba(test_scaled)[0]

CLASS_NAMES  = ['Normal', 'High Stress', 'High Risk']
CLASS_ICONS  = ['🟢', '🟡', '🔴']

print('=== Student Stress Prediction ===')
print(f'  Result     : {CLASS_ICONS[pred_class]} {CLASS_NAMES[pred_class]}')
print(f'  Confidence : {pred_proba[pred_class]*100:.1f}%')
print()

print('  Class probabilities:')
for i, (name, prob) in enumerate(zip(CLASS_NAMES, pred_proba)):
    bar = '█' * int(prob * 30)
    print(f'    {CLASS_ICONS[i]} {name:12s} : {bar:<30s} {prob*100:.1f}%')