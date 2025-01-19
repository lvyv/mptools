#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@File    : t_factory.py
@Time    : 2025/01/17 10:00
@Author  : Awen
@Description: This script demonstrates how to use the multiprocessing
              module to share configuration data between processes.
              It includes examples of using Manager to create shared
              dictionaries. It's also a test for the factory pattern.
@Usage   : Run this script using Python 3.x. Ensure that the required
            modules are installed.
@License : MIT License
"""

import multiprocessing
from multiprocessing import Manager
import time


# Define example classes
class ObjTracker:
    def __init__(self, config):
        self.config = config

    def run(self, name):
        timestamp = int(time.time())
        self.config.update({name: timestamp})
        return f'ObjTracker instance for {name}, Config: {self.config}'


class AnotherClass:
    def __init__(self, config):
        self.config = config

    def run(self, name):
        return f"AnotherClass instance for {name}, Config: {self.config}"


# Factory to dynamically create class instances
class Factory:
    @staticmethod
    def create_instance(class_name, config):
        """
        Dynamically create an instance of the specified class.

        Args:
            class_name (str): The name of the class to instantiate.
            config (dict): Configuration data shared across processes.

        Returns:
            object: An instance of the requested class.
        """
        classes = globals()
        if class_name in classes and callable(classes[class_name]):
            return classes[class_name](config)
        raise ValueError(f"Class '{class_name}' not found.")


# Worker function for multiprocessing.Pool
def worker(class_name, config, worker_name):
    """
    Worker function that instantiates a class and performs a task.

    Args:
        class_name (str): The name of the class to instantiate.
        config (dict): Shared configuration data.
        worker_name (str): Name of the worker.

    Returns:
        str: Result of the worker task.
    """
    instance = Factory.create_instance(class_name, config)
    return instance.run(worker_name)


if __name__ == "__main__":
    # Shared configuration data
    manager = Manager()
    shared_config = manager.dict({"api_key": "12345-ABCDE", "timeout": 30})

    # Define worker arguments
    tasks = [
        ("ObjTracker", shared_config, "Worker-1"),
        ("AnotherClass", shared_config, "Worker-2"),
        ("ObjTracker", shared_config, "Worker-3"),
        ("AnotherClass", shared_config, "Worker-4"),
    ]

    # Create a multiprocessing pool
    with multiprocessing.Pool(processes=4) as pool:
        # Use starmap_async to process tasks asynchronously
        async_result = pool.starmap_async(worker, tasks)

        # Wait for the result and retrieve it
        results = async_result.get()

    # Output results
    for result in results:
        print(result)
