#!/usr/bin/env python3
"""
Fine-tuning script for Whisper models.
This script fine-tunes a pre-trained Whisper model on custom command data
to improve accuracy for specific voice patterns and commands.
"""

import os
import json
import argparse
import torch
import whisper
import numpy as np
import logging
from tqdm import tqdm
from datasets import Dataset, Audio
from transformers import WhisperProcessor, WhisperForConditionalGeneration
from transformers import Seq2SeqTrainer, Seq2SeqTrainingArguments

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('finetune.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def load_dataset(dataset_path, sample_rate=16000):
    """Load dataset from JSON file"""
    # Get the base directory from the dataset path
    base_dir = os.path.dirname(dataset_path)
    
    # Load the dataset file
    with open(dataset_path, 'r') as f:
        data = json.load(f)
        
    # Normalize paths
    for item in data:
        if not os.path.isabs(item['audio_path']):
            item['audio_path'] = os.path.join(base_dir, item['audio_path'])
            
    # Validate dataset
    valid_data = []
    for item in data:
        if os.path.exists(item['audio_path']):
            valid_data.append(item)
        else:
            logger.warning(f"File not found: {item['audio_path']}")
            
    if not valid_data:
        raise ValueError("No valid audio files found in dataset")
        
    logger.info(f"Loaded dataset with {len(valid_data)} valid entries")
    
    # Convert to HuggingFace dataset
    hf_dataset = Dataset.from_list(valid_data)
    
    # Add audio loading capability
    hf_dataset = hf_dataset.cast_column("audio_path", Audio(sampling_rate=sample_rate))
    
    return hf_dataset

def prepare_dataset(dataset, processor):
    """Prepare dataset for fine-tuning"""
    # Function to preprocess a dataset example
    def prepare_example(example):
        # Load audio
        audio = example["audio_path"]
        
        # Extract input features
        input_features = processor(
            audio["array"], 
            sampling_rate=audio["sampling_rate"], 
            return_tensors="pt"
        ).input_features[0]
        
        # Tokenize text
        labels = processor.tokenizer(example["text"]).input_ids
        
        return {
            "input_features": input_features,
            "labels": labels
        }
    
    # Apply preprocessing
    processed_dataset = dataset.map(
        prepare_example,
        remove_columns=["audio_path", "text"],
        num_proc=1  # Increase for multi-processing
    )
    
    return processed_dataset

def fine_tune_whisper(args):
    """Fine-tune Whisper model on custom dataset"""
    logger.info(f"Starting fine-tuning with base model {args.base_model}")
    
    # Create output directory if it doesn't exist
    if not os.path.exists(args.output_dir):
        os.makedirs(args.output_dir)
    
    # Load the pre-trained model and processor
    logger.info("Loading pre-trained model and processor")
    model_name = f"openai/whisper-{args.base_model}"
    
    processor = WhisperProcessor.from_pretrained(model_name)
    model = WhisperForConditionalGeneration.from_pretrained(model_name)
    
    # Load and preprocess the dataset
    logger.info("Loading and preprocessing dataset")
    dataset = load_dataset(args.dataset)
    processed_dataset = prepare_dataset(dataset, processor)
    
    # Split dataset into train and validation
    if args.validation_split > 0:
        splits = processed_dataset.train_test_split(
            test_size=args.validation_split,
            seed=42
        )
        train_dataset = splits["train"]
        eval_dataset = splits["test"]
    else:
        train_dataset = processed_dataset
        eval_dataset = None
    
    logger.info(f"Training on {len(train_dataset)} examples")
    if eval_dataset:
        logger.info(f"Evaluating on {len(eval_dataset)} examples")
    
    # Define training arguments
    training_args = Seq2SeqTrainingArguments(
        output_dir=args.output_dir,
        per_device_train_batch_size=args.batch_size,
        gradient_accumulation_steps=args.gradient_accumulation_steps,
        learning_rate=args.learning_rate,
        warmup_steps=args.warmup_steps,
        num_train_epochs=args.epochs,
        evaluation_strategy="epoch" if eval_dataset else "no",
        save_strategy="epoch",
        logging_dir=os.path.join(args.output_dir, "logs"),
        logging_steps=10,
        load_best_model_at_end=eval_dataset is not None,
        fp16=torch.cuda.is_available() and args.fp16,
        optim="adamw_torch",
        report_to="tensorboard"
    )
    
    # Initialize trainer
    trainer = Seq2SeqTrainer(
        model=model,
        args=training_args,
        train_dataset=train_dataset,
        eval_dataset=eval_dataset,
    )
    
    # Start training
    logger.info("Starting training")
    trainer.train()
    
    # Save the fine-tuned model
    logger.info(f"Saving fine-tuned model to {args.output_dir}")
    model.save_pretrained(args.output_dir)
    processor.save_pretrained(args.output_dir)
    
    # Save fine-tuning arguments
    with open(os.path.join(args.output_dir, 'finetune_args.json'), 'w') as f:
        json.dump(vars(args), f, indent=2)
    
    logger.info("Fine-tuning completed successfully")
    
    return model, processor

def test_model(model, processor, test_audio, device=None):
    """Test the fine-tuned model on a sample audio file"""
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
        
    model = model.to(device)
    
    logger.info(f"Testing model on {test_audio}")
    try:
        # Load audio
        audio = whisper.load_audio(test_audio)
        
        # Process audio with default settings
        result = model.generate(
            processor(audio, return_tensors="pt", sampling_rate=16000).input_features.to(device)
        )
        
        # Decode prediction
        predicted_text = processor.batch_decode(
            result, skip_special_tokens=True
        )[0]
        
        logger.info(f"Prediction: {predicted_text}")
        return predicted_text
    except Exception as e:
        logger.error(f"Error testing model: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Fine-tune Whisper model on custom commands")
    
    # Model arguments
    parser.add_argument(
        "--base-model", 
        type=str, 
        default="base", 
        choices=["tiny", "base", "small", "medium", "large"],
        help="Base Whisper model to fine-tune"
    )
    
    # Dataset arguments
    parser.add_argument(
        "--dataset", 
        type=str, 
        required=True, 
        help="Path to JSON dataset"
    )
    parser.add_argument(
        "--validation-split", 
        type=float, 
        default=0.1,
        help="Fraction of data to use for validation (0 for no validation)"
    )
    
    # Training arguments
    parser.add_argument(
        "--output-dir", 
        type=str, 
        default="./fine_tuned_model",
        help="Directory to save the fine-tuned model"
    )
    parser.add_argument(
        "--epochs", 
        type=int, 
        default=3,
        help="Number of training epochs"
    )
    parser.add_argument(
        "--batch-size", 
        type=int, 
        default=4,
        help="Batch size for training"
    )
    parser.add_argument(
        "--learning-rate", 
        type=float, 
        default=1e-5,
        help="Learning rate for fine-tuning"
    )
    parser.add_argument(
        "--warmup-steps", 
        type=int, 
        default=50,
        help="Number of warmup steps"
    )
    parser.add_argument(
        "--gradient-accumulation-steps", 
        type=int, 
        default=2,
        help="Number of gradient accumulation steps"
    )
    parser.add_argument(
        "--fp16", 
        action="store_true",
        help="Use mixed precision training"
    )
    
    # Testing arguments
    parser.add_argument(
        "--test-audio", 
        type=str, 
        help="Path to audio file for testing after fine-tuning"
    )
    
    args = parser.parse_args()
    
    # Fine-tune the model
    model, processor = fine_tune_whisper(args)
    
    # Test the model if a test file is provided
    if args.test_audio and os.path.exists(args.test_audio):
        test_model(model, processor, args.test_audio)
    
if __name__ == "__main__":
    main() 