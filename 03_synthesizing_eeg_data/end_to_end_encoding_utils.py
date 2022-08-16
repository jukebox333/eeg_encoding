def load_images(args):
	"""Load and preprocess the training, validation and test images.

	Parameters
	----------
	args : Namespace
		Input arguments.

	Returns
	-------
	X_train : list of tensor
		Training images.
	X_val : list of tensor
		Validation images.
	X_test : list of tensor
		Test images.

	"""

	import os
	from torchvision import transforms
	from tqdm import tqdm
	from PIL import Image

	### Define the image preprocesing ###
	preprocess = transforms.Compose([
		transforms.Resize((224,224)),
		transforms.ToTensor(),
		transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
	])

	### Load and preprocess the training and validation images ###
	img_dirs = os.path.join(args.project_dir, 'image_set',
		'training_images')
	image_list = []
	for root, dirs, files in os.walk(img_dirs):
		for file in files:
			if file.endswith(".jpg"):
				image_list.append(os.path.join(root,file))
	image_list.sort()
	X_train = []
	X_val = []
	for i, image in enumerate(tqdm(image_list)):
		img = Image.open(image).convert('RGB')
		img = preprocess(img)
		# Use the first image exemplar of each training object concept for
		# validation
		if i % 10 == 0:
			X_val.append(img)
		else:
			X_train.append(img)

	### Load and preprocess the test images ###
	img_dirs = os.path.join(args.project_dir, 'image_set',
		'test_images')
	image_list = []
	for root, dirs, files in os.walk(img_dirs):
		for file in files:
			if file.endswith(".jpg"):
				image_list.append(os.path.join(root,file))
	image_list.sort()
	X_test = []
	for image in tqdm(image_list):
		img = Image.open(image).convert('RGB')
		img = preprocess(img)
		X_test.append(img)

	### Output ###
	return X_train, X_val, X_test


def load_eeg_data(args):
	"""Load the EEG training, validation and test data.

	Parameters
	----------
	args : Namespace
		Input arguments.

	Returns
	-------
	y_train : float
		Training EEG data.
	y_val : float
		Validation EEG data.
	y_test : float
		Test EEG data.
	ch_names : list of str
		EEG channel names.
	times : float
		EEG time points.

	"""

	import os
	import numpy as np
	import torch

	### Load the EEG training data ###
	data_dir = os.path.join('eeg_dataset', 'preprocessed_data', 'sub-'+
		format(args.sub,'02'))
	training_file = 'preprocessed_eeg_training.npy'
	data = np.load(os.path.join(args.project_dir, data_dir, training_file),
		allow_pickle=True).item()
	y_train = data['preprocessed_eeg_data']
	ch_names = data['ch_names']
	times = data['times']
	# Average across repetitions
	y_train = np.mean(y_train, 1)

	### Create the validation partition from the training data ###
	idx_val = np.arange(0, len(y_train), 10)
	y_val = y_train[idx_val]
	y_train = np.delete(y_train, idx_val, 0)
	# Convert the data to tensor format
	y_val = torch.tensor(np.float32(y_val))
	y_train = torch.tensor(np.float32(y_train))

	### Load the EEG test data ###
	test_file = 'preprocessed_eeg_test.npy'
	data = np.load(os.path.join(args.project_dir, data_dir, test_file),
		allow_pickle=True).item()
	y_test = data['preprocessed_eeg_data']
	# Average across repetitions
	y_test = np.mean(y_test, 1)
	# Convert the data to tensor format
	y_test = torch.tensor(np.float32(y_test))

	### Output ###
	return y_train, y_val, y_test, ch_names, times


def create_dataloader(args, time_point, X_train, X_val, X_test, y_train, y_val,
	y_test):
	"""Put the training, validation and test data into a PyTorch-compatible
	Dataloader format.

	Parameters
	----------
	args : Namespace
		Input arguments.
	time_point : int
		Modeled EEG time point.
	X_train : list of tensor
		Training images.
	X_val : list of tensor
		Validation images.
	X_test : list of tensor
		Test images.
	y_train : float
		Training EEG data.
	y_val : float
		Validation EEG data.
	y_test : float
		Test EEG data.

	Returns
	----------
	train_dl : Dataloader
		Training Dataloader.
	val_dl : Dataloader
		Validation Dataloader.
	test_dl : Dataloader
		Test Dataloader.

	"""

	import torch
	from torch.utils.data import Dataset
	from torch.utils.data import DataLoader

	### Dataset class ###
	class EegDataset(Dataset):
		def __init__(self, X, y, modeled_time_points, transform=None,
			target_transform=None):
			self.modeled_time_points = modeled_time_points
			self.X = X_train
			if self.modeled_time_points == 'single':
				self.y = y[:,:,time_point]
			elif self.modeled_time_points == 'all':
				self.y = torch.reshape(y, (y.shape[0],-1))
			self.transform = transform
			self.target_transform = target_transform

		def __len__(self):
			return len(self.y)

		def __getitem__(self, idx):
			image = self.X[idx]
			target = self.y[idx]
			if self.transform:
				image = self.transform(image)
			if self.target_transform:
				target = self.target_transform(target)
			return image, target

	### Convert the data to PyTorch's Dataset format ###
	train_ds = EegDataset(X_train, y_train, args.modeled_time_points)
	val_ds = EegDataset(X_val, y_val, args.modeled_time_points)
	test_ds = EegDataset(X_test, y_test, args.modeled_time_points)

	### Convert the Datasets to PyTorch's Dataloader format ###
	train_dl = DataLoader(train_ds, batch_size=args.batch_size, shuffle=True,
		pin_memory=True)
	val_dl = DataLoader(val_ds, batch_size=val_ds.__len__(), shuffle=False,
		pin_memory=True)
	test_dl = DataLoader(test_ds, batch_size=test_ds.__len__(), shuffle=False,
		pin_memory=True)

	### Output ###
	return train_dl, val_dl, test_dl
