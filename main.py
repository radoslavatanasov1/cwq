import click
import json
import requests
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.circuit.library import GroverOperator
from qiskit_algorithms import AmplificationProblem, Grover
from qiskit.primitives import StatevectorSampler

# Define a Profile class to hold API key and proxy settings
class Profile:
    def __init__(self, api_key, proxy, proxy_username=None, proxy_password=None):
        self.api_key = api_key
        self.proxy = proxy
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.current_keyspace = None

    def assign_keyspace(self, lower_bound, upper_bound):
        self.current_keyspace = (lower_bound, upper_bound)

    def get_proxy_dict(self):
        """Return the proxy dictionary for the requests library."""
        if self.proxy:
            # Add proxy authentication credentials if provided
            if self.proxy_username and self.proxy_password:
                proxy_auth = f"{self.proxy_username}:{self.proxy_password}@"
                proxy_url = self.proxy.replace("://", f"://{proxy_auth}")
            else:
                proxy_url = self.proxy
            return {"http": proxy_url, "https": proxy_url}
        return None

    def run_grover_search(self, lower_bound, upper_bound, iterations=2):
        """Run a Grover search within the assigned keyspace."""
        num_qubits = len(format(int(upper_bound, 16), 'b'))  # Determine qubits needed for range
        oracle_circuit = QuantumCircuit(num_qubits)

        # Create the oracle for the range
        for i, bit in enumerate(format(int(lower_bound, 16), 'b')):
            if bit == '0':
                oracle_circuit.x(i)

        oracle_circuit.h(num_qubits - 1)
        oracle_circuit.mcx(list(range(num_qubits - 1)), num_qubits - 1)
        oracle_circuit.h(num_qubits - 1)

        # Construct Grover's operator and create the main quantum circuit
        grover_operator = GroverOperator(oracle_circuit)
        qc = QuantumCircuit(num_qubits)
        for _ in range(iterations):
            qc = qc.compose(grover_operator)

        # Define the is_good_state function to mark good states
        def is_good_state(bitstring):
            return lower_bound <= bitstring <= upper_bound

        # Setup the problem and run Grover's algorithm
        problem = AmplificationProblem(oracle_circuit, is_good_state=is_good_state)
        sampler = StatevectorSampler()
        grover = Grover(sampler=sampler)
        result = grover.amplify(problem)
        return result

# Load profiles from a configuration file
def load_profiles(filename):
    with open(filename, 'r') as file:
        data = json.load(file)
        profiles = [
            Profile(
                profile["api_key"],
                profile["proxy"],
                profile.get("proxy_username"),
                profile.get("proxy_password")
            ) for profile in data
        ]
    return profiles

# Command-line interface for managing profiles and running Grover's algorithm
@click.group()
def cli():
    pass

# Command to assign keyspace to a profile
@click.command()
@click.option('--profile-id', type=int, help='Profile ID to assign keyspace to')
@click.option('--lower-hex', default='0x100', help='Lower bound of the range in hexadecimal (e.g., 0x100)')
@click.option('--upper-hex', default='0x1FF', help='Upper bound of the range in hexadecimal (e.g., 0x1FF)')
def assign_keyspace(profile_id, lower_hex, upper_hex):
    profiles = load_profiles('profiles.json')
    profiles[profile_id].assign_keyspace(lower_hex, upper_hex)
    print(f"Assigned keyspace {lower_hex} to {upper_hex} to Profile {profile_id}")

# Command to run Grover's algorithm using a specific profile
@click.command()
@click.option('--profile-id', type=int, help='Profile ID to use for running Grover search')
@click.option('--iterations', default=2, help='Number of Grover iterations to perform')
def run_grover(profile_id, iterations):
    profiles = load_profiles('profiles.json')
    profile = profiles[profile_id]
    
    # Run Grover's algorithm within the assigned keyspace
    if profile.current_keyspace:
        lower_hex, upper_hex = profile.current_keyspace
        result = profile.run_grover_search(lower_hex, upper_hex, iterations)
        print(f"Results for Profile {profile_id}: {result}")
    else:
        print(f"Profile {profile_id} does not have an assigned keyspace.")

# Register CLI commands
cli.add_command(assign_keyspace)
cli.add_command(run_grover)

if __name__ == '__main__':
    cli()
