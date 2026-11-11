# CVT Visual Concept Map Editor

CVT Visual Concept Map Editor is a Python application built using PyQt6 that allows users to create and edit visual concept maps.

It provides an intuitive interface for creating nodes, linking them with text, and forming propositions. 

The application supports saving, loading, exporting, and zooming functionalities.

## Features

- **Concept Nodes**: Create rounded rectangles representing concepts.
- **Text Nodes**: Add linking words between concepts.
- **Propositions**: Form connections between concepts and linking words.
- **Editing**: Double-click to edit text of nodes or linking words.
- **Arrow Creation**: Right-click to start and end arrows between nodes.
- **Validation**: Arrows must follow the structure: concept → linking words → concept (not enforced!).
- **Zooming**: Zoom in and out for better visualization.
- **Scrolling**: Scroll the canvas for large diagrams.
- **Export**: Save diagrams as JSON, export tuples as text files, or export diagrams as SVG.

You can export the map as a comma delimited text file where each proposition in the map has the form:

`concept1, linking words, concept2`

This is very useful for inputting into Generative AI.

We wrote this tool for readers of our book "Generative Analysis". You can find out much more about Concept Maps anand d proositions how to use them effectively with Generative AI in the book.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd <repository-folder>
   ```

2. Install dependencies:
   ```bash
   pip install pyqt6
   ```

## Usage

1. Run the application:
   ```bash
   python cvt_concept_map_visual_editor.py
   ```

2. Use the toolbar buttons to:
   - Add concept nodes or linking words nodes.
   - Delete selected nodes or arrows.
   - Save or load diagrams.
   - Export tuples or diagrams as SVG.
   - Zoom in or out.

## File Formats

- **JSON**: Save and load diagrams.
- **TXT**: Export list of propositions in the format: `concept1, linking words, concept2`.
- **SVG**: Export diagrams as scalable vector graphics.

## Keyboard and Mouse Controls

- **Double-click**: Edit nodes or linking words.
- **Right-click**: Start or end arrows.
- **Left-click**: Select nodes or arrows.

## Screenshots

*(Add screenshots of the application interface here)*

## License

This project is licensed under the MIT License. See the `LICENSE` file for details.

## Contributing

Contributions are welcome! Feel free to open issues or submit pull requests.

## Contact

For questions or feedback, please contact via GitHub.
