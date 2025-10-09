import os
import logging
import random
import uuid
from pydicom import dcmread
from pydicom.uid import JPEGBaseline
from pynetdicom import AE, StoragePresentationContexts
from pynetdicom.sop_class import CTImageStorage
from pynetdicom import debug_logger
from pydicom.uid import ExplicitVRLittleEndian
from pynetdicom.sop_class import XRayAngiographicImageStorage

debug_logger()

modalities = ['CT', 'MR', 'CR', 'US', 'XA']
body_parts = ['HEAD', 'CHEST', 'ABDOMEN', 'KNEE', 'SPINE', 'PELVIS', 'FOOT']
first_names = ['Alex', 'Jordan', 'Taylor', 'Morgan', 'Jamie', 'Casey', 'Riley', 'Cameron', 'Quinn', 'Avery']
last_names = ['Smith', 'Johnson', 'Lee', 'Brown', 'Garcia', 'Martinez', 'Davis', 'Miller', 'Wilson', 'Anderson']
patient_name = f"{random.choice(last_names)}^{random.choice(first_names)}"

selected_modality = random.choice(modalities)
selected_body_part = random.choice(body_parts)
patient_name = f"{random.choice(last_names)}^{random.choice(first_names)}"
patient_id = str(random.randint(1000000, 9999999))  # 7-digit ID


CLIENT_AE_TITLE = 'SIMCLIENT'
IMPLEMENTATION_CLASS_UID = '1.2.826.0.1.3680043.9.7435'
IMPLEMENTATION_VERSION_NAME = 'SIMCLIENT_1.0'


def send_dicom_to_pacs(dicom_folder, pacs_ip, pacs_port, pacs_ae_title):
    # Create an Application Entity
    ae = AE(ae_title=CLIENT_AE_TITLE)
    ae.implementation_class_uid = IMPLEMENTATION_CLASS_UID
    ae.implementation_version_name = IMPLEMENTATION_VERSION_NAME[:16]
    ae.supported_contexts = StoragePresentationContexts

    # Add the requested transfer syntax for the X-Ray Angiographic Image Storage context
    ae.add_requested_context('1.2.840.10008.5.1.4.1.1.12.1', [JPEGBaseline])
    ae.add_requested_context('1.2.840.10008.5.1.4.1.1.1.1',  [JPEGBaseline])

 # Add TLS layer for encryption
    # tls_context = build_context('TLS')
    # tls_context.load_cert_chain(pacs_certificate, private_key)
    # ae.add_supported_context(CTImageStorage, tls_context)

    # Connect to the PACS server
    assoc = ae.associate(pacs_ip, pacs_port, ae_title=pacs_ae_title)
    if assoc.is_established:
        print('Connected to the PACS server.')

        # Iterate over DICOM files in the folder
        for filename in os.listdir(dicom_folder):
            if filename.endswith('.DCM'):
                dicom_file = os.path.join(dicom_folder, filename)

                # Read the DICOM file
                dataset = dcmread(dicom_file)
                dataset.PatientName = patient_name
                dataset.PatientID = patient_id
                dataset.SOPClassUID = XRayAngiographicImageStorage
                dataset.SOPInstanceUID = f"1.2.826.0.1.3680043.2.1125.{uuid.uuid4().int >> 64}"
                dataset.StudyInstanceUID = f"1.2.826.0.1.3680043.2.1125.{uuid.uuid4().int >> 64}"
                dataset.SeriesInstanceUID = f"1.2.826.0.1.3680043.2.1125.{uuid.uuid4().int >> 64}"
                dataset.Modality = selected_modality
                dataset.BodyPartExamined = selected_body_part
                dataset.Rows = 2
                dataset.Columns = 2   

                # Send the DICOM image to the PACS server
                status = assoc.send_c_store(dataset)

                # Check the status of the storage request
                if status:
                    print(f'Successfully sent {dicom_file} to the PACS server.')
                else:
                    print(f'Failed to send {dicom_file} to the PACS server.')

        # Release the association
        assoc.release()
        print('Disconnected from the PACS server.')
    else:
        print('Failed to connect to the PACS server.')

# Usage example
dicom_folder = r'/home/rmcnutt/dicom_simulation/DICOM_images'
pacs_ip = '10.10.100.88'  # Replace with the actual IP address
pacs_port = 4790  # Replace with the actual port number
pacs_ae_title = 'ORTHANC'  # Replace with the actual AE title

# pacs_certificate = '/path/to/certificate.pem'  # Replace with the path to your certificate
# private_key = '/path/to/private_key.pem'  # Replace with the path to your private key

#send_dicom_to_pacs(dicom_folder, pacs_ip, pacs_port)
send_dicom_to_pacs(dicom_folder, pacs_ip, pacs_port, pacs_ae_title)
#send_dicom_to_pacs(dicom_folder, pacs_ip, pacs_port, pacs_ae_title, pacs_certificate, private_key)
