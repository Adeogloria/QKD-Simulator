import random
import secrets
import hmac
import hashlib
import cirq
import tkinter as tk
from tkinter import ttk
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import threading
import math 

SCENARIO_NORMAL = "normal"
SCENARIO_NOISY = "noisy"
SCENARIO_EAVESDROP = "eavesdrop"

def secure_bit():
    return secrets.randbits(1)

def secure_bits(n):
    return [secrets.randbits(1) for _ in range(n)]

def sign_message(message: bytes, auth_key: bytes) -> bytes:
    return hmac.new(auth_key, message, hashlib.sha256).digest()

def verify_message(message: bytes, tag: bytes, auth_key: bytes) -> bool:
    expected = sign_message(message, auth_key)
    return hmac.compare_digest(expected, tag)

def apply_noise(bits, noise_rate):
    noisy = []
    for b in bits:
        if random.random() < noise_rate:
            noisy.append(1 - b)  # flip
        else:
            noisy.append(b)
    return noisy

def distance_to_loss_params(distance_km, attenuation_db_per_km=0.2, detector_efficiency=0.85):
    """
    Convert fiber distance to equivalent noise and photon survival rate.
    Standard single-mode fiber: 0.2 dB/km attenuation.
    Returns (noise_rate, survival_rate)
    """
    loss_db = attenuation_db_per_km * distance_km
    survival_rate = 10 ** (-loss_db / 10)
    effective_noise = (1 - survival_rate) * (1 - detector_efficiency)
    effective_noise = min(effective_noise, 0.30)  # cap at 30%
    return round(effective_noise, 4), round(survival_rate, 4)

def apply_photon_loss(bits, survival_rate):
    """
    Simulate photon loss: each qubit survives with probability survival_rate.
    Lost qubits are replaced with random bits (Bob detects nothing, guesses).
    Returns (surviving_bits, loss_indices)
    """
    result = []
    lost = []
    for i, bit in enumerate(bits):
        if random.random() < survival_rate:
            result.append(bit)
        else:
            result.append(secrets.randbits(1))  # random guess for lost photon
            lost.append(i)
    return result, lost

def apply_detector_inefficiency(bits, efficiency=0.85):
    """
    Simulate detector inefficiency: each arriving photon is detected
    with probability efficiency. Undetected photons become random bits.
    """
    result = []
    for bit in bits:
        if random.random() < efficiency:
            result.append(bit)
        else:
            result.append(secrets.randbits(1))
    return result



from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os

def encrypt_message(key: bytes, plaintext: str):
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce, ciphertext

def decrypt_message(key: bytes, nonce: bytes, ciphertext: bytes):
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext, None).decode()

def derive_aes_key(raw_key_bits):
    raw_bytes = bytes(raw_key_bits)
    return hashlib.sha256(raw_bytes).digest()

def alice_prepare(bits, bases):
    qubits = cirq.LineQubit.range(len(bits))
    circuit = cirq.Circuit()

    for i, (bit, basis) in enumerate(zip(bits, bases)):
        if bit == 1:
            circuit.append(cirq.X(qubits[i]))
        if basis == "X":
            circuit.append(cirq.H(qubits[i]))

    return circuit, qubits

def bob_measure(circuit, qubits, bases):
    for i, basis in enumerate(bases):
        if basis == "X":
            circuit.append(cirq.H(qubits[i]))

    circuit.append(cirq.measure(*qubits, key="m"))
    return circuit

def sift_key(alice_bits, alice_bases, bob_bits, bob_bases):
    """
    Keep only bits where Alice and Bob used the same basis.
    """
    return [
        alice_bits[i]
        for i in range(len(alice_bits))
        if alice_bases[i] == bob_bases[i]
    ]
    
def estimate_qber(alice_key, bob_key, sample_ratio=0.2):
    #Estimate the Quantum Bit Error Rate (QBER)
    #by comparing a random subset of the sifted keys.
    
    if len(alice_key) == 0:
        return 1.0  # force abort if no key remains

    sample_size = max(1, int(len(alice_key) * sample_ratio))

    errors = sum(
            1 for i in range(sample_size)
            if alice_key[i] != bob_key[i]
        )

    return errors / sample_size

def error_correction(self, sifted_key):
    """
    Perform a simple error correction on the sifted key.
    Currently uses a majority vote (repetition code).
    """
    if not sifted_key:
        return []

    # For simplicity, we just return the key itself in this example.
    # In real BB84, you would use parity checks or LDPC codes.
    return sifted_key

import hashlib  # make sure this import is at the top

def privacy_amplification(self, corrected_key):
    """
    Perform privacy amplification on the corrected key
    using SHA-256 hash. Returns a list of bits.
    """
    if not corrected_key:
        return []

    key_str = ''.join(str(bit) for bit in corrected_key)
    hash_bytes = hashlib.sha256(key_str.encode()).digest()

    # Convert hash bytes to a list of bits
    bits = []
    for byte in hash_bytes:
        bits.extend([int(b) for b in format(byte, '08b')])
    return bits

def encrypt_message_aes(key: bytes, plaintext: str):
    """
    Encrypt message using AES-GCM.
    key must be 16, 24, or 32 bytes.
    """
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode(), None)
    return nonce, ciphertext


def decrypt_message_aes(key: bytes, nonce: bytes, ciphertext: bytes):
    aesgcm = AESGCM(key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return plaintext.decode()

    
class QKDSimulator:
    def __init__(self, root):
        self.qubit_length = 254

        # Cirq qubits and simulator
        self.qubits = cirq.LineQubit.range(self.qubit_length)
        self.simulator = cirq.Simulator()

        self.root = root
        self.message_entry = None
        self.encrypt_button = None
        self.encrypted_label = None
        self.decrypted_label = None
        
        self.scenario = SCENARIO_NORMAL
        self.noise_rate = 0.05   # 5% noise (only used in noisy mode)

        self.create_gui()

    # ================= GUI =================

    def create_gui(self):
        self.root.title("Quantum Key Distribution (QKD) Simulator")

        style = ttk.Style()
        style.configure("TLabel", font=("Arial", 12))
        style.configure("TButton", font=("Arial", 12))
        

        entry_frame = ttk.Frame(self.root, padding=10)
        entry_frame.pack()

        ttk.Label(
            entry_frame,
            text="Enter your message:",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=(0, 10))

        self.message_entry = ttk.Entry(entry_frame, width=50, font=("Arial", 12))
        self.message_entry.pack(side="left", fill="x", expand=True)
        self.message_entry.bind("<Return>", lambda e: self.encrypt_message())

        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack()

        self.enter_button = ttk.Button(
            button_frame, text="Enter", command=self.encrypt_message
        )
        self.enter_button.pack()

        encrypted_frame = ttk.Frame(self.root, padding=10)
        encrypted_frame.pack()
        
        self.noise_button = ttk.Button(
            button_frame,
            text="Run Noise Sweep",
            command=self.trigger_noise_sweep
)
        self.noise_button.pack(side="left", padx=5)

        ttk.Label(
            encrypted_frame,
            text="Encrypted Message:",
            font=("Arial", 12, "bold")
        ).pack()

        self.encrypted_label = ttk.Label(encrypted_frame, text="")
        self.encrypted_label.pack()

        decrypted_frame = ttk.Frame(self.root, padding=10)
        decrypted_frame.pack()
        
        self.dist_button = ttk.Button(
            button_frame,
            text="Run Distance Experiment",
            command=self.trigger_distance_experiment
        )
        self.dist_button.pack(side="left", padx=5)

        ttk.Label(
            decrypted_frame,
            text="Decrypted Message:",
            font=("Arial", 12, "bold")
        ).pack()

        self.decrypted_label = ttk.Label(decrypted_frame, text="")
        self.decrypted_label.pack()
        
        scenario_frame = ttk.Frame(self.root, padding=10)
        scenario_frame.pack()

        ttk.Label(scenario_frame, text="Scenario:", font=("Arial", 12, "bold")).pack(side="left")
        
        self.scenario_var = tk.StringVar(value=SCENARIO_NORMAL)
        scenario_menu = ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_var,
            values=[SCENARIO_NORMAL, SCENARIO_NOISY, SCENARIO_EAVESDROP],
            state="readonly",
            width=20
        )
        
        scenario_menu.pack(side="left", padx=10)
        scenario_menu.bind("<<ComboboxSelected>>", self.on_scenario_change)

    # Add a status label to show scenario results
        self.status_label = ttk.Label(self.root, text="", font=("Arial", 11), foreground="blue")
        self.status_label.pack(pady=5)
        
        # Add this block after your existing labels in create_gui
        results_frame = ttk.LabelFrame(self.root, text="Simulation Results", padding=10)
        results_frame.pack(fill="x", padx=10, pady=10)

        self.scenario_label = ttk.Label(results_frame, text="Scenario: —", font=("Arial", 11))
        self.scenario_label.pack(anchor="w")

        self.qber_label = ttk.Label(results_frame, text="QBER: —", font=("Arial", 11))
        self.qber_label.pack(anchor="w")

        self.sifted_key_label = ttk.Label(results_frame, text="Sifted Key Length: —", font=("Arial", 11))
        self.sifted_key_label.pack(anchor="w")

        self.noise_label = ttk.Label(results_frame, text="Noise Applied: —", font=("Arial", 11))
        self.noise_label.pack(anchor="w")

        self.verdict_label = ttk.Label(results_frame, text="Verdict: —", font=("Arial", 12, "bold"))
        self.verdict_label.pack(anchor="w", pady=(5, 0))

    # ================= CORE LOGIC =================
    
    def on_scenario_change(self, event=None):
        self.scenario = self.scenario_var.get()
        self.status_label.config(text=f"Scenario set to: {self.scenario}")

    def encrypt_message(self):
        message = self.message_entry.get()
        
        if not message:
            self.verdict_label.config(text="⚠️ Please enter a message.", foreground="orange")
            return
        # Disable button to prevent double clicks
        self.enter_button.config(state="disabled", text="Running...")
        self.verdict_label.config(text="⏳ Simulating quantum channel...", foreground="blue")

         # Run simulation in background thread
        thread = threading.Thread(target=self._run_simulation, args=(message,), daemon=True)
        thread.start()
        
    def trigger_noise_sweep(self):
        print("DEBUG: trigger_noise_sweep called")
        self.verdict_label.config(
            text="⏳ Running noise sweep...", foreground="blue"
        )
        thread = threading.Thread(
            target=self._run_noise_sweep_thread,
            daemon=True
        )
        thread.start()
        
    def trigger_distance_experiment(self):
        self.verdict_label.config(
            text="⏳ Running distance experiment...", foreground="blue"
        )
        thread = threading.Thread(
            target=self._run_distance_thread, daemon=True
        )
        thread.start()
        
    def _show_noise_results(self, results):
        print("DEBUG: showing noise results")
        win = tk.Toplevel(self.root)
        win.title("Noise Sweep Results")
        win.geometry("420x300")

        cols = ["Noise (%)", "QBER (%)", "Outcome"]
        tree = ttk.Treeview(win, columns=cols, show="headings")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor="center")

        for r in results:
            color = "red" if r["outcome"] == "Abort" else "green"
            tree.insert(
                "", "end",
                values=(r["noise_rate"], r["qber"], r["outcome"]),
                tags=(color,)
            )

        tree.tag_configure("red", foreground="red")
        tree.tag_configure("green", foreground="green")

        tree.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=5)

        self.verdict_label.config(
            text="✅ Noise sweep complete", foreground="green"
        )
        
    def _run_noise_sweep_thread(self):
        try:
            results = self.run_noise_sweep()
            self.root.after(0, self._show_noise_results, results)
        except Exception as e:
            self.root.after(
                0,
                self.verdict_label.config,
                {"text": f"❌ Error: {e}", "foreground": "red"}
            )

    def _run_distance_thread(self):
        try:
            results = self.run_distance_experiment([10, 50, 100, 200])
            self.root.after(0, self._show_distance_results, results)
        except Exception as e:
            self.root.after(
                0, self.verdict_label.config,
                {"text": f"❌ Error: {e}", "foreground": "red"}
            )

    def _show_distance_results(self, results):
        win = tk.Toplevel(self.root)
        win.title("Distance Experiment Results")
        win.geometry("600x320")

        cols = ["Distance (km)", "Loss (dB)", "Survival %",
                "Noise %", "Sifted Key", "QBER %",
                "Final Key (bits)", "Outcome"]
        tree = ttk.Treeview(win, columns=cols, show="headings")

        for col in cols:
            tree.heading(col, text=col)
            tree.column(col, width=80, anchor="center")

        for r in results:
            color = "green" if r["outcome"] == "Success" else "red"
            tree.insert("", "end", values=(
                r["distance_km"], r["loss_db"],
                f"{r['survival_rate']}%", f"{r['noise_rate']}%",
                r["sifted_key_len"], f"{r['qber']}%",
                r["final_key_bits"], r["outcome"]
            ), tags=(color,))

        tree.tag_configure("green", foreground="green")
        tree.tag_configure("red",   foreground="red")
        tree.pack(fill="both", expand=True, padx=10, pady=10)
        ttk.Button(win, text="Close", command=win.destroy).pack(pady=5)
        self.verdict_label.config(
            text="✅ Distance experiment complete", foreground="green"
        )   

    def _run_simulation(self, message):
        try:
            self.scenario = self.scenario_var.get()

            alice_bits = secure_bits(self.qubit_length)
            alice_bases = ["X" if secure_bit() else "Z" for _ in range(self.qubit_length)]
            circuit, qubits = alice_prepare(alice_bits, alice_bases)

            bob_bases = ["X" if secure_bit() else "Z" for _ in range(self.qubit_length)]
            
            # Eavesdrop tracking variables
            eve_interference_count = 0
            eve_detection_count    = 0
            eve_bits               = None
            eve_bases              = None

            # --- Eavesdrop scenario ---
            if self.scenario == SCENARIO_EAVESDROP:
                eve_bases = ["X" if secure_bit() else "Z" for _ in range(self.qubit_length)]
                eve_circuit = bob_measure(cirq.Circuit(circuit), qubits, eve_bases)
                eve_result = self.simulator.run(eve_circuit, repetitions=1)
                eve_bits = list(eve_result.measurements["m"][0])
                
                # Count how many qubits Eve measured in wrong basis (interference)
                eve_interference_count = sum(
                    1 for i in range(self.qubit_length)
                    if eve_bases[i] != alice_bases[i]
            )
            
                circuit, qubits = alice_prepare(eve_bits, eve_bases)

            circuit = bob_measure(circuit, qubits, bob_bases)
            result = self.simulator.run(circuit, repetitions=1)
            bob_bits = list(result.measurements["m"][0])

            # --- Noisy scenario ---
            noise_applied = False
            if self.scenario == SCENARIO_NOISY:
                bob_bits = apply_noise(bob_bits, self.noise_rate)
                noise_applied = True

            # --- Sifting ---
            alice_key = sift_key(alice_bits, alice_bases, bob_bits, bob_bases)
            bob_key   = sift_key(bob_bits,   bob_bases,   alice_bits, alice_bases)

            # --- QBER ---
            qber = estimate_qber(alice_key, bob_key)
            
            # Count how many sifted bits were actually corrupted by Eve
            if self.scenario == SCENARIO_EAVESDROP and eve_bits is not None:
                eve_detection_count = sum(
                    1 for i in range(min(len(alice_key), len(bob_key)))
                    if alice_key[i] != bob_key[i]
                )

            # --- Schedule GUI update on main thread ---
            self.root.after(0, self._update_gui,
            qber, alice_key, bob_key, noise_applied, message,
            eve_interference_count, eve_detection_count, None
        )
        except Exception as e:
            self.root.after(0, self._update_gui, None, [], False, message, str(e))
            
            
    def _update_gui(self, qber, alice_key, bob_key, noise_applied, message, eve_interference_count, eve_detection_count, error):
        # Re-enable button
        self.enter_button.config(state="normal", text="Enter")

        if error:
            self.verdict_label.config(text=f"❌ Error: {error}", foreground="red")
            return
        
        sifted_length    = len(alice_key)
        interference_pct = (
            (eve_interference_count / self.qubit_length) * 100
            if eve_interference_count > 0 else 0
        )
        detection_pct = (
            (eve_detection_count / sifted_length * 100)
            if sifted_length > 0 and eve_detection_count > 0 else 0
        )

        # Update diagnostic labels
        self.scenario_label.config(
            text=f"Scenario: {self.scenario.upper()}")
        self.qber_label.config(
            text=f"QBER: {qber:.2%}",
            foreground="red" if qber > 0.11 else "green"
        )
        self.sifted_key_label.config(
            text=f"Sifted Key Length: {len(alice_key)} bits")
        self.noise_label.config(
            text=f"Noise Applied: {'Yes (' + str(int(self.noise_rate * 100)) + '% flip rate)' if noise_applied else 'No'}",
            foreground="orange" if noise_applied else "black"
        )
        
        # Eve-specific labels (only meaningful in eavesdrop mode)
        if self.scenario == SCENARIO_EAVESDROP:
            self.scenario_label.config(
                text=(
                    f"Scenario: EAVESDROP | "
                    f"Eve intercepted: {eve_interference_count} qubits "
                    f"({interference_pct:.1f}%) | "
                    f"Bits corrupted: {eve_detection_count} "
                    f"({detection_pct:.1f}%)"
                )
            )

        # Abort if QBER too high
        if qber > 0.11:
            self.verdict_label.config(
                text=f"🚨 ABORT — {'Eavesdropping detected!' if self.scenario == SCENARIO_EAVESDROP else 'Channel too noisy!'}",
                foreground="red"
            )
            self.encrypted_label.config(text="N/A - Transmission Collapsed")
            self.decrypted_label.config(text="N/A - Transmission Collapsed")
            # Show collapse popup only for eavesdrop
            if self.scenario == SCENARIO_EAVESDROP:
                self._show_collapse_window(
                    qber, alice_key, bob_key,
                    eve_interference_count, eve_detection_count
                ) 
                return

        # Key processing
        corrected_key = self.error_correction(alice_key)
        final_key = self.privacy_amplification(corrected_key)
        aes_key = bytes(final_key[:32])

        nonce, ciphertext = encrypt_message_aes(aes_key, message)
        plaintext = decrypt_message_aes(aes_key, nonce, ciphertext)

        self.verdict_label.config(
            text="✅ Secure transmission successful — QBER within safe limits.",
            foreground="green"
        )
        self.encrypted_label.config(text=ciphertext.hex())
        self.decrypted_label.config(text=plaintext)   
        
    def _show_collapse_window(self, qber, alice_key, bob_key,
                           eve_interference_count, eve_detection_count):
         # Create popup window
        win = tk.Toplevel(self.root)
        win.title("⚠️ Quantum Transmission Collapse Report")
        win.geometry("520x420")
        win.resizable(False, False)

        ttk.Label(
            win,
            text="TRANSMISSION COLLAPSED",
            font=("Arial", 15, "bold"),
            foreground="red"
        ).pack(pady=(15, 5))

        ttk.Label(
            win,
            text="Eavesdropper detected via quantum state collapse",
            font=("Arial", 11),
            foreground="gray"
        ).pack(pady=(0, 15))

        # Stats frame
        stats_frame = ttk.LabelFrame(win, text="Collapse Statistics", padding=10)
        stats_frame.pack(fill="x", padx=20, pady=5)

        total_qubits        = self.qubit_length
        sifted_length       = len(alice_key)
        interference_pct    = (eve_interference_count / total_qubits) * 100
        detection_pct       = (eve_detection_count / sifted_length * 100) if sifted_length > 0 else 0

        stats = [
            ("Total Qubits Transmitted",       f"{total_qubits}"),
            ("Qubits Eve Intercepted (wrong basis)",
                                           f"{eve_interference_count} "
                                           f"({interference_pct:.1f}%)"),
            ("Sifted Key Length",              f"{sifted_length} bits"),
            ("Bits Corrupted by Eve",          f"{eve_detection_count} "
                                           f"({detection_pct:.1f}% of sifted key)"),
            ("QBER",                           f"{qber:.2%}"),
            ("QBER Threshold",                 "11.00%"),
            ("Collapse Triggered",             "YES — Transmission Aborted"),
        ]

        for label, value in stats:
            row = ttk.Frame(stats_frame)
            row.pack(fill="x", pady=2)
            ttk.Label(row, text=label + ":", width=38, anchor="w").pack(side="left")
            ttk.Label(
                row, text=value,
                foreground="red" if "YES" in value or "QBER" == label else "black",
                font=("Arial", 10, "bold")
            ).pack(side="left")

        # Explanation frame
        explain_frame = ttk.LabelFrame(win, text="Why Transmission Collapsed", padding=10)
        explain_frame.pack(fill="x", padx=20, pady=10)

        explanation = (
            "When Eve intercepted qubits, she was forced to measure them.\n"
            "Measuring a qubit COLLAPSES its quantum state — it can no\n"
            "longer carry the original superposition Alice encoded.\n\n"
            "Eve then re-sent qubits based on her (wrong) measurements,\n"
            f"introducing ~{detection_pct:.1f}% errors into the sifted key.\n\n"
            "Since QBER exceeded 11%, Alice and Bob detected the collapse\n"
            "and aborted transmission to prevent key compromise."
        )

        ttk.Label(
            explain_frame,
            text=explanation,
            font=("Arial", 10),
            justify="left"
        ).pack(anchor="w")

        ttk.Button(win, text="Close", command=win.destroy).pack(pady=10)
           
    def prepare_circuit(self, key):
        circuit = cirq.Circuit()

        for i, bit in enumerate(key):
            if bit == 1:
                circuit.append(cirq.X(self.qubits[i]))

        # Example gate mix (your original logic)
        circuit.append(cirq.H.on_each(*self.qubits))
        circuit.append(cirq.X(self.qubits[1]))
        circuit.append(cirq.Y(self.qubits[2]))
        circuit.append(cirq.Z(self.qubits[3]))

        circuit.append(cirq.measure(*self.qubits, key="m"))
        return circuit

    def measure_qubits(self, circuit):
        result = self.simulator.run(circuit, repetitions=1)
        bob_bits = result.measurements["m"][0]
        return list(bob_bits)

    # ================= CLASSICAL =================
    
    def run_distance_experiment(self, distances_km=[10, 50, 100, 200]):
        """
        Run BB84 simulation at multiple fiber distances.
        Returns a list of result dicts for each distance.
        """
        results = []

        for dist in distances_km:
            noise_rate, survival_rate = distance_to_loss_params(dist)

            alice_bits  = secure_bits(self.qubit_length)
            alice_bases = ["X" if secure_bit() else "Z"
                       for _ in range(self.qubit_length)]
            circuit, qubits = alice_prepare(alice_bits, alice_bases)

            bob_bases = ["X" if secure_bit() else "Z"
                     for _ in range(self.qubit_length)]
            circuit   = bob_measure(circuit, qubits, bob_bases)
            result    = self.simulator.run(circuit, repetitions=1)
            bob_bits  = list(result.measurements["m"][0])

            # Apply photon loss
            bob_bits, lost_indices = apply_photon_loss(bob_bits, survival_rate)

            # Apply detector inefficiency
            bob_bits = apply_detector_inefficiency(bob_bits, efficiency=0.85)

            # Apply channel noise
            bob_bits = apply_noise(bob_bits, noise_rate)

            alice_key = sift_key(alice_bits, alice_bases, bob_bits, bob_bases)
            bob_key   = sift_key(bob_bits,   bob_bases,  alice_bits, alice_bases)
            qber      = estimate_qber(alice_key, bob_key)

            if qber > 0.11 or len(alice_key) < 10:
                final_key_length = 0
                outcome = "Abort"
            else:
                corrected = self.error_correction(alice_key)
                final     = self.privacy_amplification(corrected)
                final_key_length = len(final)
                outcome = "Success"

            results.append({
                "distance_km":    dist,
                "loss_db":        round(0.2 * dist, 1),
                "survival_rate":  round(survival_rate * 100, 1),
                "noise_rate":     round(noise_rate * 100, 1),
                "sifted_key_len": len(alice_key),
                "qber":           round(qber * 100, 2),
                "final_key_bits": final_key_length,
                "outcome":        outcome,
                })

        return results
    
    def run_noise_sweep(self, noise_levels=None):
        """
        Run BB84 at multiple noise rates to generate QBER vs noise data.
        """
        if noise_levels is None:
            noise_levels = [0.0, 0.02, 0.05, 0.07, 0.09, 0.11, 0.14, 0.20, 0.25]

        results = []
        for p in noise_levels:
            alice_bits  = secure_bits(self.qubit_length)
            alice_bases = ["X" if secure_bit() else "Z"
                       for _ in range(self.qubit_length)]
            circuit, qubits = alice_prepare(alice_bits, alice_bases)

            bob_bases = ["X" if secure_bit() else "Z"
                     for _ in range(self.qubit_length)]
            circuit   = bob_measure(circuit, qubits, bob_bases)
            sim_result = self.simulator.run(circuit, repetitions=1)
            bob_bits   = list(sim_result.measurements["m"][0])

            bob_bits   = apply_noise(bob_bits, p)
            alice_key  = sift_key(alice_bits, alice_bases, bob_bits, bob_bases)
            bob_key    = sift_key(bob_bits,   bob_bases,  alice_bits, alice_bases)
            qber       = estimate_qber(alice_key, bob_key)

            results.append({
                "noise_rate": round(p * 100, 1),
                "qber":       round(qber * 100, 2),
                "outcome":    "Abort" if qber > 0.11 else "Proceed"
            })

        return results
    
    def run_eve_sweep(self, interception_rates=None):
        """
        Run BB84 with Eve intercepting varying fractions of qubits.
        interception_rates: list of floats 0.0–1.0
        """
        if interception_rates is None:
            interception_rates = [0.0, 0.20, 0.44, 0.50, 0.75, 1.0]

        results = []
        for eve_fraction in interception_rates:
            alice_bits  = secure_bits(self.qubit_length)
            alice_bases = ["X" if secure_bit() else "Z"
                            for _ in range(self.qubit_length)]
            circuit, qubits = alice_prepare(alice_bits, alice_bases)

            # Eve intercepts only a fraction of qubits
            eve_bases = ["X" if secure_bit() else "Z"
                            for _ in range(self.qubit_length)]
            eve_circuit = bob_measure(
                cirq.Circuit(circuit), qubits, eve_bases
            )
            eve_result = self.simulator.run(eve_circuit, repetitions=1)
            eve_bits   = list(eve_result.measurements["m"][0])

            # Only re-prepare the intercepted fraction
            intercepted_indices = random.sample(
                range(self.qubit_length),
                int(eve_fraction * self.qubit_length)
            )
            modified_bits  = alice_bits[:]
            modified_bases = alice_bases[:]
            for i in intercepted_indices:
                modified_bits[i]  = eve_bits[i]
                modified_bases[i] = eve_bases[i]

            circuit, qubits = alice_prepare(modified_bits, modified_bases)
            bob_bases = ["X" if secure_bit() else "Z"
                            for _ in range(self.qubit_length)]
            circuit   = bob_measure(circuit, qubits, bob_bases)
            bob_result = self.simulator.run(circuit, repetitions=1)
            bob_bits   = list(bob_result.measurements["m"][0])

            alice_key = sift_key(alice_bits, alice_bases, bob_bits, bob_bases)
            bob_key   = sift_key(bob_bits,   bob_bases,  alice_bits, alice_bases)
            qber      = estimate_qber(alice_key, bob_key)

            results.append({
                "eve_interception_pct":  round(eve_fraction * 100, 1),
                "theoretical_qber_pct":  round(eve_fraction * 25, 2),
                "observed_qber_pct":     round(qber * 100, 2),
                "outcome": "Abort" if qber > 0.11 else "Proceed"
            })

        return results


    def generate_random_key(self):
        return secure_bits(self.qubit_length)

    def compare_bases(self, alice, bob):
        return [i for i in range(len(alice)) if alice[i] == bob[i]]

    def sift_key(self, key, indices):
        return [key[i] for i in indices]

    def detect_eavesdropping(self, alice, bob, sifted_key):
        if len(sifted_key) < self.qubit_length // 3:
            print("⚠️ Potential eavesdropping detected!")
        else:
            print("✅ No evidence of eavesdropping.")

    def classical_communication(self, message):
        bits = []
        for char in message:
            bits.extend([int(b) for b in bin(ord(char))[2:].zfill(8)])
        return bits

    def encrypt_message_bits(self, message, key):
        return [(bit ^ key[i % len(key)]) for i, bit in enumerate(message)]

    def decrypt_message(self, ciphertext, key):
        return [(bit ^ key[i % len(key)]) for i, bit in enumerate(ciphertext)]

    def binary_to_ascii(self, bits):
        chars = []
        for i in range(0, len(bits), 8):
            chars.append(chr(int("".join(map(str, bits[i:i+8])), 2)))
        return "".join(chars)

    def error_correction(self, key):
        return key  # placeholder (no real EC implemented)

    def privacy_amplification(self, key):
        hashed = hashlib.sha256("".join(map(str, key)).encode()).digest()
        return [b & 1 for b in hashed]

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    root = tk.Tk()
    app = QKDSimulator(root)
    app.run()