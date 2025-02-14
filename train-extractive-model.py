import os
import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display
from tqdm import tqdm

import torch
from transformers import AdamW
from torch.utils.data import dataloader
from dataset import ExtractiveDataset
from model.kobert import KoBERTforExtractiveSummarization

def train(epoch, model, optimizer, train_loader, save_step, save_ckpt_path, train_step = 0):
    losses = []
    train_start_index = train_step+1 if train_step != 0 else 0
    total_train_step = len(train_loader)
    model.train()

    with tqdm(total= total_train_step, desc=f"Train({epoch})") as pbar:
        pbar.update(train_step)
        for i, data in enumerate(train_loader, train_start_index):

            optimizer.zero_grad()
            outputs = model(**data)

            loss = outputs['loss']
            losses.append(loss.item())

            loss.backward()
            optimizer.step()

            pbar.update(1)
            pbar.set_postfix_str(f"Loss: {loss.item():.3f} ({np.mean(losses):.3f})")

            if i >= total_train_step or i % save_step == 0:
                torch.save({
                    'epoch': epoch,  # 현재 학습 epoch
                    'model_state_dict': model.state_dict(),  # 모델 저장
                    'optimizer_state_dict': optimizer.state_dict(),  # 옵티마이저 저장
                    'loss': loss.item(),  # Loss 저장
                    'losses':losses,
                    'train_step': i,  # 현재 진행한 학습
                    'total_train_step': len(train_loader)  # 현재 epoch에 학습 할 총 train step
                }, save_ckpt_path)

    return np.mean(losses)



if __name__ == '__main__':
    checkpoint_path ="./checkpoint"
    save_ckpt_path = f"{checkpoint_path}/kobert-extractive.pth"

    n_epoch = 5          # Num of Epoch
    batch_size = 2      # 배치 사이즈
    device = "cuda" if torch.cuda.is_available() else "cpu"
    save_step = 100 # 학습 저장 주기
    learning_rate = 5e-5  # Learning Rate

    # WellnessTextClassificationDataset 데이터 로더
    dataset = ExtractiveDataset(data_path='./data/train_test.jsonl', device=device)
    train_loader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

    model = KoBERTforExtractiveSummarization()
    model.to(device)

    # Prepare optimizer and schedule (linear warmup and decay)
    no_decay = ['bias', 'LayerNorm.weight']
    optimizer_grouped_parameters = [
        {'params': [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
         'weight_decay': 0.01},
        {'params': [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)], 'weight_decay': 0.0}
    ]
    optimizer = AdamW(optimizer_grouped_parameters, lr=learning_rate)

    pre_epoch, pre_loss, train_step = 0, 0, 0
    losses = []

    # if os.path.isfile(save_ckpt_path):
    #     checkpoint = torch.load(save_ckpt_path, map_location=device)
    #     pre_epoch = checkpoint['epoch']
    #     pre_loss = checkpoint['loss']
    #     losses = checkpoint['losses']
    #     train_step =  checkpoint['train_step']
    #     total_train_step =  checkpoint['total_train_step']
    #
    #     model.load_state_dict(checkpoint['model_state_dict'])
    #     optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
    #
    #     print(f"load pretrain from: {save_ckpt_path}, epoch={pre_epoch}, loss={pre_loss}")
    #     # best_epoch += 1

    offset = pre_epoch
    for step in range(n_epoch):
        epoch = step + offset
        loss = train(epoch, model, optimizer, train_loader, save_step, save_ckpt_path, train_step)
        losses.append(loss)

    # data
    data = {
        "loss": losses
    }
    df = pd.DataFrame(data)
    display(df)

    # graph
    plt.figure(figsize=[12, 4])
    plt.plot(losses, label="loss")
    plt.legend()
    plt.xlabel('Epoch')
    plt.ylabel('Loss')
    plt.show()
