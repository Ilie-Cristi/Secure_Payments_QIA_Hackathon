from random import randint
from netqasm.sdk import Qubit
from netqasm.sdk.classical_communication.message import StructuredMessage
import hmac
import sqlite3
import hashlib
from squidasm.sim.stack.common import LogManager
from squidasm.sim.stack.program import Program, ProgramContext, ProgramMeta


class TTPProgram(Program):
    PEER_NAME = "Client"

    def __init__(self, num_qubits):
        self.logger = LogManager.get_stack_logger(self.__class__.__name__)

        #The number of teleported qubits 
        self._num_teleported_qubits = num_qubits


    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="controller_program",
            csockets=[self.PEER_NAME],
            epr_sockets=[self.PEER_NAME],
            max_qubits=self._num_teleported_qubits,
        )

    def run(self, context: ProgramContext):
        csocket = context.csockets[self.PEER_NAME]
        epr_socket = context.epr_sockets[self.PEER_NAME]
        connection = context.connection

        b = [randint(0,1) for _ in range(self._num_teleported_qubits)]
        B = [randint(0,1) for _ in range(self._num_teleported_qubits)]

        print(f'Bitstream:{b}\nBasis:    {B}')

        for i in range(self._num_teleported_qubits):
            q = Qubit(connection)
            if b[i] == 1:
                q.X()
            if B[i] == 0:
                q.H()

            # Create EPR pairs
            epr = epr_socket.create_keep()[0]
            # Teleport
            q.cnot(epr)
            q.H()
            m1 = q.measure()
            m2 = epr.measure()
            yield from connection.flush()
            # Send the correction information
            m1, m2 = int(m1), int(m2)

            self.logger.info(
                f"Performed teleportation protocol with measured corrections: m1 = {m1}, m2 = {m2}"
            )

            csocket.send_structured(StructuredMessage("Corrections", f"{m1},{m2}"))

        
        return b,B


class ClientProgram(Program):
    PEER_NAME = "TTP"

    def __init__(self, num_qubits):
        self.logger = LogManager.get_stack_logger(self.__class__.__name__)
        self._num_teleported_qubits = num_qubits

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="controller_program",
            csockets=[self.PEER_NAME],
            epr_sockets=[self.PEER_NAME],
            max_qubits=self._num_teleported_qubits,
        )

    def run(self, context: ProgramContext):
        csocket = context.csockets[self.PEER_NAME]
        epr_socket = context.epr_sockets[self.PEER_NAME]
        connection = context.connection

        # Define the client's secret C
        C = 'TopSecretC'.encode()
        
        # Use the merchant identification
        M = 'Merchant1ID'.encode()

        # Create the hmac based on the number of qubits sent (insecure implementation)
        fullmac = hmac.digest(C,M,'sha512')
        n = self._num_teleported_qubits
        if n%8 != 0:
            m = fullmac[:n//8]+(fullmac[n//8+1]>>(8-n%8)).to_bytes(1,'big')
        else:
            m = fullmac[:n//8]

        measured_basis = []


        k = []
        for i in range(n):
            epr = epr_socket.recv_keep()[0]
            yield from connection.flush()
            self.logger.info("Created EPR pair")


            # Get the corrections
            msg = yield from csocket.recv_structured()
            print(msg)
            assert isinstance(msg, StructuredMessage)
            m1, m2 = msg.payload.split(",")
            self.logger.info(f"Received corrections: {m1}, {m2}")
            if int(m2) == 1:
                self.logger.info("performing X correction")
                epr.X()
            if int(m1) == 1:
                self.logger.info("performing Z correction")
                epr.Z()

            # Define the measurement basis
            if (m[i // 8] >> (8 - i % 8)) % 2 == 0:
                epr.H()

            measured_basis.append((m[i // 8] >> (8 - i % 8)) % 2)
            em = epr.measure()
            yield from connection.flush()
            k.append(int(em))
            
        
        print(f'Client bitstream: {k}\nClient basis:     {measured_basis}')
        return k, hashlib.md5(C).digest()
    

class MaliciousClientProgram(Program):
    PEER_NAME = "TTP"

    def __init__(self, num_qubits):
        self.logger = LogManager.get_stack_logger(self.__class__.__name__)
        self._num_teleported_qubits = num_qubits

    @property
    def meta(self) -> ProgramMeta:
        return ProgramMeta(
            name="controller_program",
            csockets=[self.PEER_NAME],
            epr_sockets=[self.PEER_NAME],
            max_qubits=self._num_teleported_qubits,
        )

    def run(self, context: ProgramContext):
        csocket = context.csockets[self.PEER_NAME]
        epr_socket = context.epr_sockets[self.PEER_NAME]
        connection = context.connection

        # Define the client's secret C
        C = 'TopSecretC'.encode()
        
        # Use the merchant1 identification
        M1 = 'Merchant1ID'.encode()

        # Use the merchant2 identification
        M2 = 'Merchant2ID'.encode()        

        # Create the hmacs based on the number of qubits sent (insecure implementation)
        # Craft the malitious base for measurement
        fullmac1 = hmac.digest(C,M1,'sha512')
        fullmac2 = hmac.digest(C,M2,'sha512')
        n = self._num_teleported_qubits
        if n % 8 != 0:
            base1 = fullmac1[:n//8]+(fullmac1[n//8+1]>>(8-n%8)).to_bytes(1,'big')
        else:
            base1 = fullmac1[:n//8]

        if n % 8 != 0:
            base2 = fullmac2[:n//8]+(fullmac2[n//8+1]>>(8-n%8)).to_bytes(1,'big')
        else:
            base2 = fullmac2[:n//8]
        
        measured_basis = []

        k = []
        for i in range(n):
            epr = epr_socket.recv_keep()[0]
            yield from connection.flush()
            self.logger.info("Created EPR pair")


            # Get the corrections
            msg = yield from csocket.recv_structured()
            print(msg)
            assert isinstance(msg, StructuredMessage)
            m1, m2 = msg.payload.split(",")
            self.logger.info(f"Received corrections: {m1}, {m2}")
            if int(m2) == 1:
                self.logger.info("performing X correction")
                epr.X()
            if int(m1) == 1:
                self.logger.info("performing Z correction")
                epr.Z()
            if i % 2 == 0:
                measured_basis.append((base1[i // 8] >> (8 - i % 8)) % 2)
            else:
                measured_basis.append((base2[i // 8] >> (8 - i % 8)) % 2)

            # Define the measurement basis
            if measured_basis[i] == 0:
                epr.H()
            
             
            em = epr.measure()
            yield from connection.flush()
            k.append(int(em))
            
        
        print(f'Client bitstream: {k}\nClient basis:     {measured_basis}')
        return k, hashlib.md5(C).digest()

#Define the TTP entity
class TTP():
    def __init__(self,n,b,B,k,M,CID):
        self.MerchantID = M
        self.ClientKey = k
        self.ClientID = CID
        self._num_teleported_qubits = n
        self.initial_bitstream = b
        self.initial_basis = B
        self.BER = 0

    def verify_P(self):
        """
        This method will return the bit error rate for the qbits measured in the same basis
        """
        C = 'TopSecretC'.encode()
        if self.ClientID == hashlib.md5(C).digest():
            fullmac = hmac.digest(C,self.MerchantID,'sha512')
            n = self._num_teleported_qubits
            if n % 8 != 0:
                m = fullmac[:n//8]+(fullmac[n//8+1]>>(8-n%8)).to_bytes(1,'big')
            else:
                m = fullmac[:n//8]

            measured_basis = []
            self.mismatches = 0
            for i in range(n):
                measured_basis.append((m[i // 8] >> (8 - i % 8)) % 2)
                if self.initial_basis[i] == measured_basis[i] and self.ClientKey[i] != self.initial_bitstream[i]:
                    self.mismatches += 1

            print(measured_basis)
            self.BER = self.mismatches / n

        return self.BER



# Define the merchant entity
class Merchant():
    def __init__(self,k,CID):
        self.key = k
        self.merchantID = 'Merchant1ID'.encode()
        self.clientID = CID

    def return_to_bank(self):
        return self.key, self.merchantID, self.clientID
    
