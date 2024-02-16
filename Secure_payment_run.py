from Secure_payment_TTP_Client import MaliciousClientProgram, TTPProgram, ClientProgram, TTP, Merchant
import logging
from squidasm.run.stack.run import run
from squidasm.run.stack.config import StackNetworkConfig


# Create a network configuration
cfg = StackNetworkConfig.from_file("Secure_payment.yaml")

# Define the number of qubits used for |P>
num_qubits = 200 

# Create instances of programs to run
Client_program = MaliciousClientProgram(num_qubits)
TTP_program = TTPProgram(num_qubits)

# toggle logging. Set to logging.INFO for logging of events.
Client_program.logger.setLevel(logging.ERROR)
TTP_program.logger.setLevel(logging.ERROR)

# Run the simulation. Programs argument is a mapping 
# of network node labels to programs to run on that node
# As we cannot make use of three channels, we return 
# the needed information for later use
Client_step1, TTP_step1  = run(
    config=cfg,
    programs={"TTP": TTP_program, "Client": Client_program},
    num_times=1,
)

# Keep the initial bitstream and the initial basis
b = TTP_step1[0][0]
B = TTP_step1[0][1]

# Keep the key and the client ID in order to send them to the merchant
k = Client_step1[0][0]
CID = Client_step1[0][1]

# Send the key and CID to the Merchant 1
Merchant1 = Merchant(k,CID)

# The key, merchant ID and client ID sent from merchant to bank
k_r = Merchant1.return_to_bank()[0]
M_r = Merchant1.return_to_bank()[1]
CID_r = Merchant1.return_to_bank()[2]

# Create a TTP instance named Bank and send the key, CID and merchant ID
# The initial bitstream and the initial basis vector were kept in memory
# to verify the validity of the transaction

Bank = TTP(num_qubits, b, B, k_r, M_r, CID_r)

print(Bank.verify_P())
