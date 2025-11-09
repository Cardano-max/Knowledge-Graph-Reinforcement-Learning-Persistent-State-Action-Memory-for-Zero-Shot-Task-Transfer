"""
Custom TMRL trainer with JSON logging to database container
Hooks into TMRL's training loop to log episodes, states, and metrics
"""
import os
import json
import time
from datetime import datetime
import sys

DATABASE_PATH = os.getenv('DATABASE_PATH', '/shared-data')

class JSONLogger:
    """Logs training data to JSON files in database volume"""
    
    def __init__(self, base_path):
        self.base_path = base_path
        self.episode_count = 0
        self.step_count = 0
        self.last_log_time = time.time()
        
        # Create directory structure
        os.makedirs(f"{base_path}/episodes", exist_ok=True)
        os.makedirs(f"{base_path}/states", exist_ok=True)
        os.makedirs(f"{base_path}/actions", exist_ok=True)
        os.makedirs(f"{base_path}/metrics", exist_ok=True)
        
        print(f"[DATABASE] JSON Logger initialized")
        print(f"[DATABASE] Storage path: {base_path}")
        
    def log_sample(self, sample_data):
        """Log training sample"""
        try:
            filename = f"{self.base_path}/states/sample_{self.step_count:08d}.json"
            
            # Convert to serializable format
            data = {
                'sample_id': self.step_count,
                'timestamp': datetime.now().isoformat(),
                'data': str(sample_data)[:500]  # Truncate for storage
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.step_count += 1
            
            # Log every 100 samples
            if self.step_count % 100 == 0:
                print(f"[DATABASE] Logged {self.step_count} samples")
                
        except Exception as e:
            print(f"[DATABASE] Error logging sample: {e}")
        
    def log_episode(self, episode_num, total_reward, steps):
        """Log episode summary"""
        try:
            filename = f"{self.base_path}/episodes/episode_{episode_num:06d}.json"
            
            data = {
                'episode_id': episode_num,
                'timestamp': datetime.now().isoformat(),
                'total_reward': float(total_reward),
                'steps': int(steps)
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            self.episode_count = episode_num
            print(f"[DATABASE] Logged episode {episode_num}: reward={total_reward:.2f}, steps={steps}")
            
        except Exception as e:
            print(f"[DATABASE] Error logging episode: {e}")
        
    def log_metrics(self, metrics_dict):
        """Log training metrics"""
        try:
            # Only log periodically (every 10 seconds)
            current_time = time.time()
            if current_time - self.last_log_time < 10:
                return
            
            self.last_log_time = current_time
            
            timestamp = int(time.time())
            filename = f"{self.base_path}/metrics/metrics_{timestamp}.json"
            
            data = {
                'timestamp': datetime.now().isoformat(),
                'metrics': metrics_dict
            }
            
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"[DATABASE] Logged metrics: memory_len={metrics_dict.get('memory_len', 'N/A')}")
            
        except Exception as e:
            print(f"[DATABASE] Error logging metrics: {e}")

# Initialize logger
print("[DATABASE] Initializing JSON database logger...")
logger = JSONLogger(DATABASE_PATH)

# Write initial status
status_file = f"{DATABASE_PATH}/status.json"
with open(status_file, 'w') as f:
    json.dump({
        'status': 'initialized',
        'timestamp': datetime.now().isoformat(),
        'database_path': DATABASE_PATH
    }, f, indent=2)

print("[DATABASE] Database logging enabled")
print(f"[DATABASE] Status file created: {status_file}")

# Monkey-patch TMRL's TrainingOffline class to intercept data
print("[TRAINER] Patching TMRL training loop for database logging...")

from tmrl.training_offline import TrainingOffline

# Save original run_epoch method
original_run_epoch = TrainingOffline.run_epoch

def patched_run_epoch(self, interface):
    """Patched version that logs data"""
    
    # Log metrics before training
    try:
        metrics = {
            'memory_len': len(self.memory) if hasattr(self, 'memory') else 0,
            'epoch': self.epoch if hasattr(self, 'epoch') else 0,
        }
        logger.log_metrics(metrics)
    except Exception as e:
        print(f"[DATABASE] Error in pre-epoch logging: {e}")
    
    # Call original method
    result = original_run_epoch(self, interface)
    
    # Log metrics after training
    try:
        if hasattr(result, 'to_dict'):
            metrics_dict = result.to_dict()
        elif isinstance(result, dict):
            metrics_dict = result
        else:
            metrics_dict = {'result': str(result)}
        
        logger.log_metrics(metrics_dict)
    except Exception as e:
        print(f"[DATABASE] Error in post-epoch logging: {e}")
    
    return result

# Apply monkey patch
TrainingOffline.run_epoch = patched_run_epoch
print("[TRAINER] Training loop patched successfully")

# Also patch memory append to log samples
try:
    from tmrl.memory import TorchMemory
    
    original_append = TorchMemory.append
    
    def patched_append(self, buffer):
        """Patched append that logs samples"""
        result = original_append(self, buffer)
        
        # Log sample periodically
        if len(self) % 50 == 0:  # Every 50 samples
            try:
                logger.log_sample({
                    'memory_size': len(self),
                    'buffer_size': len(buffer) if hasattr(buffer, '__len__') else 'unknown'
                })
            except Exception as e:
                print(f"[DATABASE] Error logging sample: {e}")
        
        return result
    
    TorchMemory.append = patched_append
    print("[TRAINER] Memory logging patched successfully")
    
except Exception as e:
    print(f"[TRAINER] Could not patch memory logging: {e}")

# Now run standard TMRL trainer
print("[TRAINER] Starting TMRL trainer with database logging...")

# Import and parse arguments properly
import argparse
from tmrl import __main__ as tmrl_main_module


# Create argument parser (complete with ALL TMRL arguments)
parser = argparse.ArgumentParser()
parser.add_argument('--server', action='store_true', help='launches the server')
parser.add_argument('--trainer', action='store_true', help='launches the trainer')
parser.add_argument('--worker', action='store_true', help='launches a worker')
parser.add_argument('--test', action='store_true', help='runs a simple training test')
parser.add_argument('--benchmark', action='store_true', help='runs benchmark')
parser.add_argument('--expert', action='store_true', help='runs expert')
parser.add_argument('--wandb', action='store_true', help='enables wandb logging')
parser.add_argument('--profile', action='store_true', help='enables profiling')

# Set trainer mode
sys.argv = ['tmrl', '--trainer']
args = parser.parse_args()

# Call TMRL main with parsed args
tmrl_main_module.main(args)
