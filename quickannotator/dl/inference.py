import torch
import numpy as np
from .dataset import TileDataset

def run_inference(model, dataset):
    dataloader = DataLoader(dataset, batch_size=1, shuffle=False)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = model.to(device)
    model.eval()
    with torch.no_grad():
        for images, masks, weights in dataloader:
            images = images.to(device)
            outputs = model(images)
            outputs = outputs.squeeze().detach().cpu().numpy()
            yield outputs