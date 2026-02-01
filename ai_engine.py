import numpy as np
from sklearn.ensemble import IsolationForest
import logging

class AIEngine:
    def __init__(self):
        # We store a separate model for each device (AID)
        self.models = {} 
        self.data_buffers = {}
        self.training_threshold = 25  # Packets needed to learn "Normal"
        self.is_trained = {}

    def parse_features(self, val_str):
        """ Extracts numerical features from the text payload """
        try:
            features = []
            # 1. PARSE SERVER (CPU & Temp)
            if "CPU" in val_str:
                # Format: "CPU:65%|Temp:35.5C"
                parts = val_str.split('|')
                cpu = float(parts[0].split(':')[1].replace('%', ''))
                temp = float(parts[1].split(':')[1].replace('C', ''))
                features = [cpu, temp]
            
            # 2. PARSE HVAC (RPM)
            elif "FAN" in val_str:
                # Format: "FAN:4500RPM|PWR:Active"
                parts = val_str.split('|')
                rpm = float(parts[0].split(':')[1].replace('RPM', ''))
                # Encode Power: Active=1, Off=0
                pwr = 1.0 if "Active" in parts[1] else 0.0
                features = [rpm, pwr]

            return features
        except Exception as e:
            return None

    def analyze(self, aid, val_str):
        """ Returns (Status, Anomaly_Score) """
        features = self.parse_features(val_str)
        
        # If data isn't numeric (e.g., Door Logs), skip AI
        if not features:
            return "SKIPPED", 0.0

        # Initialize Device Memory
        if aid not in self.data_buffers:
            self.data_buffers[aid] = []
            self.is_trained[aid] = False
            # Isolation Forest: Efficient at spotting outliers
            self.models[aid] = IsolationForest(n_estimators=100, contamination=0.1, random_state=42)

        # PHASE 1: LEARNING (Calibration)
        if not self.is_trained[aid]:
            self.data_buffers[aid].append(features)
            progress = len(self.data_buffers[aid])
            
            if progress >= self.training_threshold:
                # Train the model on the gathered history
                X = np.array(self.data_buffers[aid])
                self.models[aid].fit(X)
                self.is_trained[aid] = True
                logging.info(f"🧠 AI TRAINING COMPLETE for {aid[:8]}...")
                return "TRAINED", 0.0
            else:
                return f"LEARNING ({progress}/{self.training_threshold})", 0.0

        # PHASE 2: DETECTION (Real-time)
        else:
            X_new = np.array([features])
            prediction = self.models[aid].predict(X_new)[0] # 1 = Normal, -1 = Anomaly
            score = self.models[aid].decision_function(X_new)[0]
            
            if prediction == -1:
                return "ANOMALY", round(score, 4)
            else:
                return "NORMAL", round(score, 4)