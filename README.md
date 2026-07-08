# rynaki

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/release/python-380/)

An unofficial, robust, and asynchronous-friendly Python API wrapper for the popular online game Akinator.

`rynaki` is designed to be simple and intuitive, allowing developers to easily integrate the Akinator game into their own applications. It is built on top of `cloudscraper` to handle Cloudflare's anti-bot protection, ensuring reliable communication with the Akinator servers.

## Features

-   **Asynchronous Support**: Built with `asyncio` in mind for high-performance applications.
-   **Theme Selection**: Supports `characters`, `objects`, and `animals` themes.
-   **Full Game Control**: Includes functions to start games, answer questions, go back, and handle guesses.
-   **Cloudflare Bypass**: Uses `cloudscraper` to seamlessly bypass Cloudflare's IUAM challenges.
-   **Robust Error Handling**: Custom exceptions for clear and predictable error management.

## Documentation

For a complete guide, including detailed class and method references, please visit the official documentation:

**[rynaki.readthedocs.io](https://rynaki.readthedocs.io)**

## Installation

Install `rynaki` easily using pip:

```bash
pip install rynaki
```

## Quickstart

Here is a simple example of how to use `rynaki` in an asynchronous application:

```python
import asyncio
from rynaki import Akinator, AkinatorError

async def main():
    try:
        # Initialize the game in English with the 'characters' theme
        aki = Akinator(theme="characters", lang="en")

        # Start the game and get the first question
        question = await asyncio.to_thread(aki.start_game)
        print(f"First Question: {question}")

        # --- Game Loop ---
        while aki.name is None:  # Loop until Akinator makes a guess
            answer = input("Your answer (y/n/idk/p/pn): ").lower()
            if answer == "stop":
                break
            
            # Post the answer and get the next question
            question = await asyncio.to_thread(aki.post_answer, answer)
            print(f"Next Question ({aki.progression:.2f}%): {question}")
        
        # --- Guess ---
        if aki.name:
            print("\n--- Akinator's Guess ---")
            print(f"Character: {aki.name}")
            print(f"Description: {aki.description}")
            if aki.photo:
                print(f"Photo: {aki.photo}")
            
            correct = input("Is this correct? (y/n): ").lower()
            if correct == 'y':
                print("Yay! I guessed it right!")
            else:
                print("Oh, you defeated me!")

    except AkinatorError as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Contributing

Contributions are welcome! If you find a bug, have a feature request, or want to improve the code, please feel free to open an issue or submit a pull request on the project's GitHub repository.

## License

This project is licensed under the MIT License. See the `LICENSE` file for more details.
