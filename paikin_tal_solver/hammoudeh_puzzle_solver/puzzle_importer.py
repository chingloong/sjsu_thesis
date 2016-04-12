"""Jigsaw Puzzle Object

.. moduleauthor:: Zayd Hammoudeh <hammoudeh@gmail.com>
"""
import copy
import os
import math
import random

import numpy
import cv2  # OpenCV
from enum import Enum

from hammoudeh_puzzle_solver.puzzle_piece import PuzzlePiece, PuzzlePieceRotation, PuzzlePieceSide


class PuzzleType(Enum):
    """
    Type of the puzzle to solve.  Type 1 has no piece rotation while type 2 allows piece rotation.
    """

    type1 = 1
    type2 = 2


class ImageColor(Enum):
    """
    Used to create solid color images for base images and for image manipulation.
    """
    black = 1


class DirectAccuracyType(Enum):
    """
    Defines the direct accuracy types.
    """
    Standard_Direct_Accuracy = 0
    Modified_Direct_Accuracy = 0


class PuzzleResultsCollection(object):
    """
    Stores all the puzzle results information in a single collection.
    """

    _PERFORM_ASSERT_CHECKS = True

    def __init__(self, pieces_partitioned_by_puzzle):
        self._puzzle_results = []

        # Iterate through all the solved puzzles
        for set_of_pieces in pieces_partitioned_by_puzzle:
            # Iterate through all of the pieces in the puzzle
            for piece in set_of_pieces:

                # Iterate through all the pieces
                puzzle_exists = False
                for i in range(0, len(self._puzzle_results)):
                    # Check if the puzzle ID matches this set of results information.
                    if piece.puzzle_id == self._puzzle_results[i].puzzle_id:
                        puzzle_exists = True
                        self._puzzle_results[i].numb_pieces += 1
                        continue

                # If the puzzle does not exist, then create a results information
                if not puzzle_exists:
                    self._puzzle_results.append(PuzzleResultsInformation(piece.puzzle_id))
                    i = len(self._puzzle_results) - 1
                    self._puzzle_results[i].numb_pieces = 1

    def calculate_accuracies(self, solved_puzzles):
        """
        Results Accuracy Calculator

        Calculates the standard direct, modified direct, and modified neighbor accuracies for a set of solved
        puzzles.

        Args:
            solved_puzzles (List[Puzzle]): A set of solved puzzles

        """
        # Iterate through each puzzle and
        for puzzle in solved_puzzles:
            # Update the puzzle results
            for i in xrange(0, len(solved_puzzles)):
                self._puzzle_results[i].resolve_direct_accuracies(puzzle)
                self._puzzle_results[i].resolve_neighbor_accuracies(puzzle)

    @property
    def results(self):
        """
        Puzzle Results Accessor

        Returns (PuzzleResultsInformation): Puzzle results information for a single puzzle.
        """
        return self._puzzle_results

    def print_results(self):
        """
        Solver Accuracy Results Printer

        Prints the accuracy results of a solver to the console.
        """

        # Iterate through each puzzle and print that puzzle's results
        for results in self._puzzle_results:
            # Print the header line
            print "Puzzle Identification Number: " + str(results.puzzle_id) + "\n"

            # Print the standard accuracy information
            for i in xrange(0, 2):

                # Select the type of direct accuracy to print.
                if i == 0:
                    acc_name = "Standard"
                    direct_acc = results.standard_direct_accuracy
                elif i == 1:
                    acc_name = "Modified"
                    direct_acc = results.modified_direct_accuracy

                # Print the selected direct accuracy type
                numb_pieces_in_original_puzzle = results.numb_pieces
                piece_count_weight = direct_acc.numb_different_puzzle + numb_pieces_in_original_puzzle
                print "Solved Puzzle ID #%d" % direct_acc.solved_puzzle_id

                print acc_name + " Direct Accuracy:\t\t%d/%d\t(%3.2f%%)" % (direct_acc.numb_correct_placements,
                                                                            piece_count_weight,
                                                                            100.0 * direct_acc.numb_correct_placements / piece_count_weight)
                print acc_name + " Numb from Diff Puzzle:\t%d/%d\t(%3.2f%%)" % (direct_acc.numb_different_puzzle,
                                                                                piece_count_weight,
                                                                                100.0 * direct_acc.numb_different_puzzle / piece_count_weight)
                print acc_name + " Numb Wrong Location:\t%d/%d\t(%3.2f%%)" % (direct_acc.numb_wrong_location,
                                                                              piece_count_weight,
                                                                              100.0 * direct_acc.numb_wrong_location / piece_count_weight)
                print acc_name + " Numb Wrong Rotation:\t%d/%d\t(%3.2f%%)" % (direct_acc.numb_wrong_rotation,
                                                                              results.numb_pieces,
                                                                              100.0 * direct_acc.numb_wrong_rotation / piece_count_weight)
                # Calculate the number of missing pieces
                numb_pieces_missing = (numb_pieces_in_original_puzzle
                                       - direct_acc.numb_pieces_from_original_puzzle_in_solved_puzzle)
                print acc_name + " Numb Pieces Missing:\t%d/%d\t(%3.2f%%)" % (numb_pieces_missing,
                                                                              numb_pieces_in_original_puzzle,
                                                                              100.0 * numb_pieces_missing / numb_pieces_in_original_puzzle)
                # Print a new line to separate the results
                print ""

            # Print the modified neighbor accuracy
            neighbor_acc = results.modified_neighbor_accuracy
            numb_pieces_in_puzzle = neighbor_acc.total_numb_included_pieces
            numb_neighbors_in_puzzle = numb_pieces_in_puzzle * PuzzlePieceSide.get_numb_sides()
            print "Solved Puzzle ID #%d" % neighbor_acc.solved_puzzle_id
            print "Neighbor Accuracy:\t\t%d/%d\t(%3.2f%%)" % (neighbor_acc.correct_neighbor_count,
                                                              numb_neighbors_in_puzzle,
                                                              100.0 * neighbor_acc.correct_neighbor_count / numb_neighbors_in_puzzle)
            numb_missing_pieces = results.numb_pieces - neighbor_acc.total_numb_included_pieces
            print "Numb Missing Pieces:\t%d/%d\t(%3.2f%%)" % (numb_missing_pieces,
                                                              results.numb_pieces,
                                                              100.0 * numb_missing_pieces / results.numb_pieces)
            numb_from_wrong_puzzle = neighbor_acc.wrong_puzzle_id
            print "Numb from Diff Puzzle:\t%d/%d\t(%3.2f%%)" % (numb_from_wrong_puzzle,
                                                                numb_pieces_in_puzzle,
                                                                100.0 * numb_from_wrong_puzzle / numb_pieces_in_puzzle)
            # Print a new line to separate the results
            print ""

            print "\n\n\n"


class PuzzleResultsInformation(object):
    """
    Encapsulates all of the accuracy results information for a puzzle.
    """

    _PERFORM_ASSERT_CHECK = True

    def __init__(self, puzzle_id):

        # Store the number of pieces and the puzzle id
        self.puzzle_id = puzzle_id
        self._numb_pieces = -1

        # Define the attributes for the standard accuracy.
        self.standard_direct_accuracy = None
        self.modified_direct_accuracy = None
        self.modified_neighbor_accuracy = None

    @property
    def numb_pieces(self):
        """
        Gets the piece count for an implicit puzzle id

        Returns (int): Number of pieces in original puzzle with this puzzle id

        """
        return self._numb_pieces

    @numb_pieces.setter
    def numb_pieces(self, value):
        self._numb_pieces = value

    def resolve_neighbor_accuracies(self, puzzle):
        """
        Neighbor Accuracy Resolved

        This function is used to calculate the neighbor accuracy of a solved puzzle and compare it to
        the results of previously calculated accuracies to select the best one.

        Args:
            puzzle (Puzzle): A solved Puzzle

        """

        # Placed piece array
        placed_piece_matrix, rotation_matrix = puzzle.build_placed_piece_info()

        # Create a temporary neighbor accuracy info
        neighbor_accuracy_info = ModifiedNeighborAccuracy(self.puzzle_id, puzzle.id_number, self.numb_pieces)

        # Iterate through the set of pieces
        for piece in puzzle.pieces:

            # Verify the puzzle identification numbers match.  If not, mark all as wrong then go to next piece
            if piece.actual_puzzle_id != self.puzzle_id:
                neighbor_accuracy_info.wrong_puzzle_id += 1
                continue

            original_neighbor_id_and_sides = piece.original_neighbor_id_numbers_and_sides
            # Sort the sides of the neighbor location to match the original order.
            neighbor_location_and_sides = piece.get_neighbor_locations_and_sides()
            neighbor_location_and_sides = sorted(neighbor_location_and_sides, key=lambda tup: tup[1].value)

            # Perform a check of the piece location information
            if PuzzleResultsInformation._PERFORM_ASSERT_CHECK:
                assert len(neighbor_location_and_sides) == len(original_neighbor_id_and_sides)
                # Verify the side in each element is the same
                for i in xrange(0, len(neighbor_location_and_sides)):
                    assert neighbor_location_and_sides[i][1] == original_neighbor_id_and_sides[i][1]

            # Iterate through all sides and check the
            for side_numb in xrange(0, len(neighbor_location_and_sides)):

                # Extract the placed piece ID.  If a cell is empty or does not exist, mark it as None
                neighbor_loc = neighbor_location_and_sides[side_numb][0]
                # Check the location is invalid.  If it is, mark the location as None.
                if (neighbor_loc[0] < 0 or neighbor_loc[1] < 0
                       or neighbor_loc[0] >= puzzle.grid_size[0] or neighbor_loc[1] >= puzzle.grid_size[1]):

                    placed_piece_id = None
                # Handle dimensions that are off the edge of the board
                else:
                    # Get the placed piece number
                    placed_piece_id = placed_piece_matrix[neighbor_loc]
                    # Handle missing pieces
                    placed_piece_id = placed_piece_id if placed_piece_id >= 0 else None

                # Check if the neighbor if the neighbor
                if(placed_piece_id == original_neighbor_id_and_sides[side_numb][0]
                   and (original_neighbor_id_and_sides[side_numb][0] is None or
                        piece.rotation.value == rotation_matrix[neighbor_location_and_sides[side_numb][0]])):

                    neighbor_accuracy_info.correct_neighbor_count += 1

                # Mark neighbor as incorrect
                else:
                    neighbor_accuracy_info.wrong_neighbor_count += 1

        # Update the best accuracy should be updated.
        if ModifiedNeighborAccuracy.check_if_update_neighbor_accuracy(self.modified_neighbor_accuracy,
                                                                      neighbor_accuracy_info):
            self.modified_neighbor_accuracy = neighbor_accuracy_info

    def resolve_direct_accuracies(self, puzzle):
        """
        Direct Accuracy Resolver

        In the case of multiple puzzles, there will be multiple direct accuracies for each

        Args:
            puzzle (Puzzle): A solved puzzle
        """

        # Get the standard direct accuracy
        new_direct_accuracy = puzzle.determine_standard_direct_accuracy(self.puzzle_id, puzzle.id_number,
                                                                        self.numb_pieces)

        # Update the stored standard direct accuracy if applicable
        if DirectAccuracyPuzzleResults.check_if_update_direct_accuracy(self.standard_direct_accuracy,
                                                                       new_direct_accuracy):
            self.standard_direct_accuracy = new_direct_accuracy

        # Modified direct accuracy is a more complicated procedure so it runs separately
        self._resolve_modified_direct_accuracy(puzzle)

    def _resolve_modified_direct_accuracy(self, puzzle):
        """
        Modified Direct Accuracy Resolver

        Specially resolves the modified direct accuracy.  This is required as as the upper left coordinate(s) need
        to be found.

        Simplified Algorithm Flow:
        * Find the piece(s) that have the minimum MANHATTAN distance from the upper left corner of the puzzle (i.e.
        location (0, 0)

        * Use any possible piece location that is within that manhattan distance as a reference point for calculating
        the direct accuracy.

        Args:
            puzzle (Puzzle): A puzzle object whose direct accuracy is being determined.

        """

        # Placed piece array
        placed_piece_matrix, _ = puzzle.build_placed_piece_info()

        # Do a Breadth first search to define the possible candidates for modified direct method
        frontier_set = [(0, 0)]
        explored_set = []
        found_dist = None
        # Continue searching until either
        while found_dist is None or (frontier_set and frontier_set[0][0] + frontier_set[0][1] <= found_dist):
            # Pop an element from the front of the list and add it to the explored set
            next_loc = frontier_set.pop(0)
            explored_set.append(next_loc)

            # Check if there is a piece in the current location
            if found_dist is None and placed_piece_matrix[next_loc] != -1:
                found_dist = next_loc[0] + next_loc[1]  # Use the manhattan distance
            else:
                # Move one piece down
                down_loc = (next_loc[0] + 1, next_loc[1])
                # Only need to check first dimension since only one that changed
                if down_loc[0] < puzzle.grid_size[0] and down_loc not in explored_set and down_loc not in frontier_set:
                    frontier_set.append(down_loc)

                # Move one piece to the right
                right_loc = (next_loc[0], next_loc[1] + 1)
                # Only need to check second dimension since only one that changed
                if right_loc[1] < puzzle.grid_size[1] and right_loc not in explored_set and right_loc not in frontier_set:
                    frontier_set.append(right_loc)

        # For all upper left coordinate candidates, determine the modified direct accuracy.
        for possible_upper_left in explored_set:
            modified_direct_accuracy = puzzle.determine_modified_direct_accuracy(self.puzzle_id, puzzle.id_number,
                                                                                 possible_upper_left,
                                                                                 self.numb_pieces)
            # Update the standard direct accuracy
            if DirectAccuracyPuzzleResults.check_if_update_direct_accuracy(self.modified_direct_accuracy,
                                                                           modified_direct_accuracy):
                self.modified_direct_accuracy = modified_direct_accuracy


class DirectAccuracyPuzzleResults(object):
    """
    Structure used for managing puzzle placement results.
    """

    def __init__(self, original_puzzle_id, solved_puzzle_id, numb_pieces_in_original_puzzle):
        self._orig_puzzle_id = original_puzzle_id
        self._solved_puzzle_id = solved_puzzle_id
        self._different_puzzle = []
        self.numb_pieces_in_original_puzzle = numb_pieces_in_original_puzzle
        self._wrong_location = []
        self._wrong_rotation = []
        self._correct_placement = []

    @property
    def original_puzzle_id(self):
        """
        Direct Accuracy Original Puzzle ID Number Accessor

        Returns (int): The puzzle ID associated with the ORIGINAL set of puzzle results
        """
        return self._orig_puzzle_id

    @property
    def solved_puzzle_id(self):
        """
        Direct Accuracy Solved Puzzle ID Number Accessor

        Returns (int): The puzzle ID associated with the SOLVED set of puzzle pieces
        """
        return self._solved_puzzle_id

    def add_wrong_location(self, piece):
        """
        Wrong Piece Location Tracker

        Adds a piece that was assigned to the wrong location number to the tracker.

        Args:
            piece (PuzzlePiece): Piece placed in the wrong LOCATION
        """
        self._wrong_location.append(piece)

    def add_different_puzzle(self, piece):
        """
        Wrong Puzzle ID Tracker

        Adds a piece that was assigned to a DIFFERENT PUZZLE ID number to the tracker.

        Args:
            piece (PuzzlePiece): Puzzle Piece that was placed with the different PUZZLE IDENTIFICATION NUMBER
        """
        self._different_puzzle.append(piece)

    def add_wrong_rotation(self, piece):
        """
        Wrong Piece Rotation Tracker

        Adds a piece that had the wrong rotation

        Args:
            piece (PuzzlePiece): Puzzle Piece that was placed with the wrong Rotation (i.e. not 0 degrees)
        """
        self._wrong_rotation.append(piece)

    def add_correct_placement(self, piece):
        """
        Correctly Placed Piece Tracker

        Adds a piece that has been placed correctly

        Args:
            piece (PuzzlePiece): Puzzle Piece that was placed CORRECTLY.
        """
        self._correct_placement.append(piece)

    @property
    def weighted_accuracy(self):
        """
        Calculates and returns the weighted accuracy score for this puzzle.

        Returns (float): Weighted accuracy score for this puzzle solution

        """
        return 1.0 * self.numb_correct_placements / (self.numb_pieces_in_original_puzzle
                                                     + self.numb_different_puzzle)

    @property
    def numb_correct_placements(self):
        """
        Number of Pieces Placed Correctly Property

        Gets the number of pieces placed correctly.

        Returns (int): Number of pieces correctly placed with the right puzzle ID, location, and rotation.
        """
        return len(self._correct_placement)

    @property
    def numb_wrong_location(self):
        """
        Number of Pieces Placed in the Wrong Location

        Gets the number of pieces placed in the wrong LOCATION.

        Returns (int): Number of pieces placed in the wrong location.
        """
        return len(self._wrong_location)

    @property
    def numb_wrong_rotation(self):
        """
        Number of Pieces with the Wrong Rotation

        Gets the number of pieces placed with the wrong ROTATION.

        Returns (int): Number of pieces placed with the incorrect rotation (i.e. not 0 degrees)
        """
        return len(self._wrong_rotation)

    @property
    def numb_different_puzzle(self):
        """
        Number of Pieces in the Wrong Puzzle

        Gets the number of pieces placed in entirely the wrong puzzle.

        Returns (int): Number of pieces placed in the wrong puzzle
        """
        return len(self._different_puzzle)

    @property
    def total_numb_included_pieces(self):
        """
        Total Number of Pieces in Results Set

        Returns (int): Total number of pieces included in this set of results.

        """
        return self.numb_pieces_from_original_puzzle_in_solved_puzzle + self.numb_different_puzzle

    @property
    def numb_pieces_from_original_puzzle_in_solved_puzzle(self):
        """
        Number of pieces from the original puzzle in the solved result

        Returns (int): Only the number of included pieces

        """
        return self.numb_correct_placements + self.numb_wrong_location + self.numb_wrong_rotation

    @staticmethod
    def check_if_update_direct_accuracy(current_best_direct_accuracy, new_direct_accuracy):
        """
        Determines whether the current best direct accuracy should be replaced with a newly calculated direct
        accuracy.

        Args:
            current_best_direct_accuracy (DirectAccuracyPuzzleResults): The best direct accuracy results
            found so far.

            new_direct_accuracy (DirectAccuracyPuzzleResults): The newly calculated best direct accuracy

        Returns (bool):
            True if the current best direct accuracy should be replaced with the new direct accuracy and False
            otherwise.
        """

        # If no best direct accuracy found so far, then just return True
        if current_best_direct_accuracy is None:
            return True

        # Get the information on the current best result
        best_numb_wrong_puzzle = current_best_direct_accuracy.numb_different_puzzle
        best_accuracy = current_best_direct_accuracy.weighted_accuracy

        # Get the information on the new direct accuracy result
        new_numb_wrong_puzzle = new_direct_accuracy.numb_different_puzzle
        new_accuracy = new_direct_accuracy.weighted_accuracy

        # Update the standard direct accuracy if applicable
        if (best_accuracy < new_accuracy or
                (best_accuracy == new_accuracy and new_numb_wrong_puzzle < best_numb_wrong_puzzle)):
            return True
        else:
            return False


class ModifiedNeighborAccuracy(object):
    """
    Encapsulating structure for the modified neighbor based accuracy approach.
    """

    def __init__(self, original_puzzle_id, solved_puzzle_id, number_of_pieces):
        self._original_puzzle_id = original_puzzle_id
        self._solved_puzzle_id = solved_puzzle_id
        self._actual_number_of_pieces = number_of_pieces
        self.wrong_puzzle_id = 0
        self.correct_neighbor_count = 0
        self.wrong_neighbor_count = 0

    @property
    def original_puzzle_id(self):
        """
        Original/Input Puzzle ID Number Property

        This method is used to access puzzle identification number information of the original/input puzzle.

        Returns (int): Original puzzle identification number associated with this set of modified neighbor
        accuracy information.
        """
        return self._original_puzzle_id

    @property
    def solved_puzzle_id(self):
        """
        Solved Puzzle ID Number Property

        This method is used to access puzzle identification number information of the puzzle that was output
        by the solved.

        Returns (int): Solved puzzle identification number associated with this set of modified neighbor
        accuracy information.
        """
        return self._solved_puzzle_id

    @property
    def total_numb_included_pieces(self):
        """
        Number of Included Pieces

        This function returns the number of puzzle pieces from the original image that were placed in the
        solved image.

        Returns (int): Number of pieces from the associated original image that are in the solved puzzle.
        """
        return (self.correct_neighbor_count + self.wrong_neighbor_count) / PuzzlePieceSide.get_numb_sides() \
               + self.wrong_puzzle_id

    @staticmethod
    def check_if_update_neighbor_accuracy(current_best_neighbor_accuracy, new_neighbor_accuracy):
        """
        Determines whether the current best direct accuracy should be replaced with a newly calculated direct
        accuracy.

        Args:
            current_best_neighbor_accuracy (ModifiedNeighborAccuracy): The best direct accuracy results
            found so far.

            new_neighbor_accuracy (ModifiedNeighborAccuracy): The newly calculated best direct accuracy

        Returns (bool):
            True if accuracy should be updated and False otherwise.
        """

        # If no best neighbor accuracy found so far, then just return True
        if current_best_neighbor_accuracy is None:
            return True

        # Get the information on the current best result
        best_piece_count = current_best_neighbor_accuracy.total_numb_included_pieces
        # best_total_errors = current_best_neighbor_accuracy.wrong_neighbor_count + \
        #                     current_best_neighbor_accuracy.wrong_puzzle_id * PuzzlePieceSide.get_numb_sides()
        best_numb_correct = current_best_neighbor_accuracy.correct_neighbor_count
        best_accuracy = 1.0 * best_numb_correct / (best_piece_count * PuzzlePieceSide.get_numb_sides())

        # Get the information on the new direct accuracy result
        new_piece_count = new_neighbor_accuracy.total_numb_included_pieces
        # new_total_errors = new_neighbor_accuracy.wrong_neighbor_count + \
        #                    new_neighbor_accuracy.total_numb_included_pieces * PuzzlePieceSide.get_numb_sides()
        new_numb_correct = new_neighbor_accuracy.correct_neighbor_count
        new_accuracy = 1.0 * new_numb_correct / (new_piece_count * PuzzlePieceSide.get_numb_sides())

        # Update the standard direct accuracy if applicable
        if (best_accuracy < new_accuracy or
                (best_accuracy == new_accuracy and new_piece_count < best_piece_count)):
            return True
        else:
            return False


class Puzzle(object):
    """
    Puzzle Object represents a single Jigsaw Puzzle.  It can import a puzzle from an image file and
    create the puzzle pieces.
    """

    print_debug_messages = True

    # DEFAULT_PIECE_WIDTH = 28  # Width of a puzzle in pixels
    DEFAULT_PIECE_WIDTH = 25  # Width of a puzzle in pixels

    # Optionally perform assertion checks.
    _PERFORM_ASSERT_CHECKS = True

    # Define the number of dimensions in the BGR space (i.e. blue, green, red)
    NUMBER_BGR_DIMENSIONS = 3

    export_with_border = True
    border_width = 3
    border_outer_stripe_width = 1

    def __init__(self, id_number, image_filename=None, piece_width=None, starting_piece_id=0):
        """Puzzle Constructor

        Constructor that will optionally load an image into the puzzle as well.

        Args:
            id_number (int): ID number for the image.  It is used for multiple image puzzles.
            image_filename (Optional str): File path of the image to load
            piece_width (Optional int): Width of a puzzle piece in pixels
            starting_piece_id (int): Identification number for the first piece in the puzzle.  If not specified,
            it default to 0.
        Returns (Puzzle):
            Puzzle divided into pieces based off the source image and the specified parameters.
        """
        # Internal Pillow Image object.
        self._id = id_number
        self._img = None
        self._img_LAB = None

        # Initialize the puzzle information.
        self._grid_size = None
        self._piece_width = piece_width if piece_width is not None else Puzzle.DEFAULT_PIECE_WIDTH
        self._img_width = None
        self._img_height = None

        # Define the upper left coordinate
        self._upper_left = (0, 0)

        # No pieces for the puzzle yet.
        self._pieces = []

        if image_filename is None:
            self._filename = ""
            return

        # Stores the image file and then loads it.
        self._filename = image_filename
        self._load_puzzle_image()

        # Make image pieces.
        self.make_pieces(starting_piece_id)

    def _load_puzzle_image(self):
        """Puzzle Image Loader

        Loads the puzzle image file a specified filename.  Loads the specified puzzle image into memory.
        It also stores information on the puzzle dimensions (e.g. width, height) into the puzzle object.

        """

        # If the filename does not exist, then raise an error.
        if not os.path.exists(self._filename):
            raise ValueError("Invalid \"%s\" value.  File does not exist" % self._filename)

        self._img = cv2.imread(self._filename)  # Note this imports in BGR format not RGB.
        if self._img is None:
            raise IOError("Unable to load the image at the specified location \"%s\"." % self._filename)

        # Get the image dimensions.
        self._img_height, self._img_width = self._img.shape[:2]

        # Make a LAB version of the image.
        self._img_LAB = cv2.cvtColor(self._img, cv2.COLOR_BGR2LAB)

    def make_pieces(self, starting_id_numb=0):
        """
        Puzzle Generator

        Given a puzzle, this function turns the puzzle into a set of pieces.

        **Note:** When creating the pieces, some of the source image may need to be discarded
        if the image size is not evenly divisible by the number of pieces specified
        as parameters to this function.

        Args:
            starting_id_numb (Optional int): Identification number of the first piece in the puzzle.  If it is not
            specified it defaults to 0.
        """
        # Calculate the piece information.
        numb_cols = int(math.floor(self._img_width / self.piece_width))  # Floor in python returns a float
        numb_rows = int(math.floor(self._img_height / self.piece_width))  # Floor in python returns a float
        if numb_cols == 0 or numb_rows == 0:
            raise ValueError("Image size is too small for the image.  Check your setup")

        # Store the grid size.
        self._grid_size = (numb_rows, numb_cols)

        # Store the original width and height and recalculate the new width and height.
        original_width = self._img_width
        original_height = self._img_height
        self._img_width = numb_cols * self.piece_width
        self._img_height = numb_rows * self.piece_width

        # Shave off the edge of the image LAB and BGR images
        puzzle_upper_left = ((original_height - self._img_height) / 2, (original_width - self._img_width) / 2)
        self._img = Puzzle.extract_subimage(self._img, puzzle_upper_left, (self._img_height, self._img_width))
        self._img_LAB = Puzzle.extract_subimage(self._img_LAB, puzzle_upper_left, (self._img_height, self._img_width))

        # Break the board into pieces.
        piece_id = starting_id_numb
        piece_size = (self.piece_width, self.piece_width)
        self._pieces = []  # Create an empty array to hold the puzzle pieces.
        for row in range(0, numb_rows):
            for col in range(0, numb_cols):
                piece_upper_left = (row * piece_size[0], col * piece_size[1])  # No longer consider upper left since board shrunk above
                piece_img = Puzzle.extract_subimage(self._img_LAB, piece_upper_left, piece_size)

                # Create the puzzle piece and assign to the location.
                location = (row, col)
                self._pieces.append(PuzzlePiece(self._id, location, piece_img,
                                                piece_id=piece_id, puzzle_grid_size=self._grid_size))
                # Increment the piece identification number
                piece_id += 1

    @property
    def id_number(self):
        """
        Puzzle Identification Number

        Gets the identification number for a puzzle.

        Returns (int): Identification number for the puzzle
        """
        return self._id

    @property
    def pieces(self):
        """
        Gets all of the pieces in this puzzle.

        Returns ([PuzzlePiece]):
        """
        return self._pieces

    @property
    def piece_width(self):
        """
        Gets the size of a puzzle piece.

        Returns (int): Height/width of each piece in pixels.

        """
        return self._piece_width

    @staticmethod
    def reconstruct_from_pieces(pieces, id_numb=-1, display_image=False):
        """
        Constructs a puzzle from a set of pieces.

        Args:
            pieces ([PuzzlePiece]): Set of puzzle pieces that comprise the puzzle.
            id_numb (Optional int): Identification number for the puzzle
            display_image (Optional Boolean): Select whether to display the image at the end of reconstruction

        Returns (Puzzle):
        Puzzle constructed from the pieces.
        """

        if len(pieces) == 0:
            raise ValueError("Error: Each puzzle must have at least one piece.")

        # Create the puzzle to return.  Give it an ID number.
        output_puzzle = Puzzle(id_numb)
        output_puzzle._id = id_numb

        # Create a copy of the pieces.
        output_puzzle._pieces = copy.deepcopy(pieces)

        # Get the first piece and use its information
        first_piece = output_puzzle._pieces[0]
        output_puzzle._piece_width = first_piece.width

        # Find the min and max row and column.
        (min_row, max_row, min_col, max_col) = output_puzzle.get_min_and_max_row_and_columns(True)

        # Normalize each piece's locations based off all the pieces in the board.
        for piece in output_puzzle._pieces:
            loc = piece.location
            piece.location = (loc[0] - min_row, loc[1] - min_col)
        output_puzzle.reset_upper_left_location()

        # Define the numpy array that will hold the reconstructed image.
        puzzle_array_size = (output_puzzle._img_height, output_puzzle._img_width)
        # noinspection PyTypeChecker
        output_puzzle._img = Puzzle.create_solid_bgr_image(puzzle_array_size, ImageColor.black)

        # Insert the pieces into the puzzle
        for piece in output_puzzle._pieces:
            output_puzzle.insert_piece_into_image(piece)

        # Convert the image to LAB format.
        output_puzzle._img_LAB = cv2.cvtColor(output_puzzle._img, cv2.COLOR_BGR2LAB)
        if display_image:
            Puzzle.display_image(output_puzzle._img)

        return output_puzzle

    def reset_upper_left_location(self):
        """
        Reset Upper Left Location

        "Upper Left" refers to the coordinate of the upper-leftmost piece.  By running this function, you
        update this reference point to (0, 0)
        """
        self._upper_left = (0, 0)

    def determine_standard_direct_accuracy(self, expected_puzzle_id, solved_puzzle_id, numb_pieces_in_original_puzzle):
        """
        Standard Direct Accuracy Finder

        Determines the accuracy of the placement using the standard direct accuracy method.

        Args:
            expected_puzzle_id (int): Expected puzzle identification number
            solved_puzzle_id (int): Identification number assigned to the solved puzzle.
            numb_pieces_in_original_puzzle (int): Number of pieces in the original puzzle

        Returns (DirectAccuracyPuzzleResults): Information regarding the direct accuracy of the placement

        """
        return self.determine_modified_direct_accuracy(expected_puzzle_id, solved_puzzle_id, (0, 0),
                                                       numb_pieces_in_original_puzzle)

    def determine_modified_direct_accuracy(self, expected_puzzle_id, solved_puzzle_id, upper_left,
                                           numb_pieces_in_original_puzzle):
        """
        Modified Direct Accuracy Finder

        Determines the accuracy of the placement using the modified direct accuracy method where by the piece accuracy
        is determined by something other than the exact upper-most left piece (i.e. location (0, 0)).

        Args:
            expected_puzzle_id (int): Expected puzzle identification number
            solved_puzzle_id (int): Solved puzzle identification number
            upper_left(Tuple[int]): In the direct method, the upper-left most location is the origin.  In the
            "Modified Direct Method", this can be a tuple in the format (row, column).
            numb_pieces_in_original_puzzle (int): Number of pieces in the original puzzle

        Returns (DirectAccuracyPuzzleResults): Information regarding the modified direct accuracy of the placement

        """
        # Optionally perform the assertion checks
        if Puzzle._PERFORM_ASSERT_CHECKS:
            assert self._upper_left == (0, 0)  # Upper left should be normalized to zero.

        # Determine the accuracy assuming the upper left is in the normal location (i.e. (0,0))
        accuracy_info = DirectAccuracyPuzzleResults(expected_puzzle_id, solved_puzzle_id,
                                                    numb_pieces_in_original_puzzle)

        # Iterate through each piece and determine its accuracy results.
        for piece in self._pieces:

            # Ensure that the puzzle ID matches the requirement
            if piece.actual_puzzle_id != expected_puzzle_id:
                accuracy_info.add_different_puzzle(piece)

            # Ensure that the puzzle piece is in the correct location
            elif not piece.is_correctly_placed(upper_left):
                accuracy_info.add_wrong_location(piece)

            # Ensure that the rotation is set to 0
            elif piece.rotation != PuzzlePieceRotation.degree_0:
                accuracy_info.add_wrong_rotation(piece)

            # Piece is correctly placed
            else:
                accuracy_info.add_correct_placement(piece)

        return accuracy_info

    def randomize_puzzle_piece_locations(self):
        """
        Puzzle Piece Location Randomizer

        Randomly assigns puzzle pieces to different locations.
        """

        # Get all locations in the image.
        all_locations = []
        for piece in self._pieces:
            all_locations.append(piece.location)

        # Shuffle the image locations
        random.shuffle(all_locations)

        # Reassign the pieces to random locations
        for i in range(0, len(self._pieces)):
            self._pieces[i].location = all_locations[i]

    def randomize_puzzle_piece_rotations(self):
        """
        Puzzle Piece Rotation Randomizer

        Assigns a random rotation to each piece in the puzzle.
        """
        for piece in self._pieces:
            piece.rotation = PuzzlePieceRotation.random_rotation()

    def get_min_and_max_row_and_columns(self, update_board_dimension_information):
        """
        Min/Max Row and Column Finder

        For a given set of pieces, this function returns the minimum and maximum of the columns and rows
        across all of the pieces.

        Args:
            update_board_dimension_information (bool): Selectively update the board dimension information (e.g.
            upper left location, grid_size, puzzle width, puzzle height, etc.).

        Returns ([int]):
        Tuple in the form: (min_row, max_row, min_column, max_column)
        """
        first_piece = self._pieces[0]
        min_row = max_row = first_piece.location[0]
        min_col = max_col = first_piece.location[1]
        for i in range(0, len(self._pieces)):
            # Verify all pieces are the same size
            if Puzzle.print_debug_messages:
                assert(self.piece_width == self._pieces[i].width)
            # Get the location of the piece
            temp_loc = self._pieces[i].location
            # Update the min and max row if needed
            if min_row > temp_loc[0]:
                min_row = temp_loc[0]
            elif max_row < temp_loc[0]:
                max_row = temp_loc[0]
            # Update the min and max column if needed
            if min_col > temp_loc[1]:
                min_col = temp_loc[1]
            elif max_col < temp_loc[1]:
                max_col = temp_loc[1]

        # If the user specified it, update the board dimension information
        if update_board_dimension_information:
            self._upper_left = (min_row, min_col)
            self._grid_size = (max_row - min_row + 1, max_col - min_col + 1)
            # Calculate the size of the image
            self._img_width = self._grid_size[1] * self.piece_width
            self._img_height = self._grid_size[0] * self.piece_width

        # Return the minimum and maximum row/column information
        return min_row, max_row, min_col, max_col

    def _assign_all_pieces_to_original_location(self):
        """Piece Correct Assignment

        Test Method Only. Assigns each piece to its original location for debug purposes.
        """
        for piece in self._pieces:
            # noinspection PyProtectedMember
            piece._assign_to_original_location()

    @property
    def grid_size(self):
        """
        Puzzle Grid Size Property

        Used to get the maximum dimensions of the puzzle in number of rows by number of columns.

        Returns ([int)): Grid size of the puzzle as a tuple in the form (number_rows, number_columns)

        """
        return self._grid_size

    # noinspection PyUnusedLocal
    @staticmethod
    def create_solid_bgr_image(size, color):
        """
        Solid BGR Image Creator

        Creates a BGR Image (i.e. NumPy) array of the specified size.

        RIGHT NOW ONLY BLACK is supported.

        Args:
            size ([int]): Size of the image in height by width
            color (ImageColor): Solid color of the image.

        Returns:
        NumPy array representing a BGR image of the specified solid color
        """
        dimensions = (size[0], size[1], Puzzle.NUMBER_BGR_DIMENSIONS)
        return numpy.zeros(dimensions, numpy.uint8)

    @staticmethod
    def extract_subimage(img, upper_left, size):
        """
        Given an image (in the form of a Numpy array) extract a subimage.

        Args:
            img : Image in the form of a numpy array.
            upper_left ([int]): upper left location of the image to extract
            size ([int]): Size of the of the sub

        Returns:
        Sub image as a numpy array
        """

        # Calculate the lower right of the image
        img_end = []
        for i in range(0, 2):
            img_end.append(upper_left[i] + size[i])

        # Return the sub image.
        return img[upper_left[0]:img_end[0], upper_left[1]:img_end[1], :]

    def insert_piece_into_image(self, piece):
        """
        Takes a puzzle piece and converts its image into BGR then adds it to the master image.

        Args:
            piece (PuzzlePiece): Puzzle piece to be inserted into the puzzle's image.
        """
        piece_loc = piece.location

        # Define the upper left corner of the piece to insert
        upper_left = (piece_loc[0] * piece.width, piece_loc[1] * piece.width)

        # Select whether to display the image rotated
        piece_bgr = piece.bgr_image()
        if piece.rotation is None or piece.rotation == PuzzlePieceRotation.degree_0:
            Puzzle.insert_subimage(self._img, upper_left, piece_bgr)
        else:
            rotated_img = numpy.rot90(piece_bgr, piece.rotation.value / 90)
            Puzzle.insert_subimage(self._img, upper_left, rotated_img)

    @staticmethod
    def insert_subimage(master_img, upper_left, subimage):
        """
        Given an image (in the form of a NumPy array), insert another image into it.

        Args:
            master_img : Image in the form of a NumPy array where the sub-image will be inserted
            upper_left ([int]): upper left location of the the master image where the sub image will be inserted
            subimage ([int]): Sub-image to be inserted into the master image.

        Returns:
        Sub image as a numpy array
        """

        # Verify the upper left input value is valid.
        if Puzzle.print_debug_messages and upper_left[0] < 0 or upper_left[1] < 0:
            raise ValueError("Error: upper left is off the image grid. Row and column must be >=0")

        # Calculate the lower right of the image
        subimage_shape = subimage.shape
        bottom_right = [upper_left[0] + subimage_shape[0], upper_left[1] + subimage_shape[1]]

        # Verify that the shape information is valid.
        if Puzzle.print_debug_messages:
            master_shape = master_img.shape
            assert master_shape[0] >= bottom_right[0] and master_shape[1] >= bottom_right[1]

        # Insert the subimage.
        master_img[upper_left[0]:bottom_right[0], upper_left[1]:bottom_right[1], :] = subimage

    @staticmethod
    def display_image(img):
        """
        Displays the image in a window for debug viewing.

        Args:
            img: OpenCV image in the form of a Numpy array

        """
        cv2.imshow('image', img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    @staticmethod
    def _save_to_file(filename, img):
        """
        Save Image to a File

        Saves any numpy array to an image file.

        Args:
            filename (str): Filename and path to save the OpenCV image.
            img: OpenCV image in the form of a Numpy array
        """
        cv2.imwrite(filename, img)

    def save_to_file(self, filename):
        """
        Save Puzzle to a File

        Saves a puzzle to the specified file name.

        Args:
            filename (str): Filename and path to save the OpenCV image.
        """
        Puzzle._save_to_file(filename, self._img)

    def build_placed_piece_info(self):
        """
        Placed Piece Info Builder

        For a puzzle, this function builds a Numpy 2d matrix showing the location of each piece.  If a possible
        puzzle piece location has no assigned piece, then the cell is filled with "None."

        Returns (Tuple[Numpy[int]]): Location of each puzzle piece in the grid
        """

        # Check whether the upper location is (0, 0)
        if Puzzle._PERFORM_ASSERT_CHECKS:
            assert self._upper_left == (0, 0)

        # Build a numpy array that is by default "None" for each cell.
        placed_piece_matrix = numpy.full(self._grid_size, -1, numpy.int32)
        placed_piece_rotation = numpy.full(self._grid_size, -1, numpy.int32)

        # For each element in the array,
        for piece in self._pieces:
            placed_piece_matrix[piece.location] = piece.original_piece_id
            placed_piece_rotation[piece.location] = piece.rotation.value

        # Return the built numpy array
        return placed_piece_matrix, placed_piece_rotation


class PuzzleTester(object):
    """
    Puzzle tester class used for debugging the solver.
    """

    PIECE_WIDTH = 5
    NUMB_PUZZLE_PIECES = 9
    GRID_SIZE = (int(math.sqrt(NUMB_PUZZLE_PIECES)), int(math.sqrt(NUMB_PUZZLE_PIECES)))
    NUMB_PIXEL_DIMENSIONS = 3

    TEST_ARRAY_FIRST_PIXEL_VALUE = 0

    # Get the information on the test image
    TEST_IMAGE_FILENAME = ".\\test\\test.jpg"
    TEST_IMAGE_WIDTH = 300
    TEST_IMAGE_HEIGHT = 200

    @staticmethod
    def build_pixel_list(start_value, is_row, reverse_list=False):
        """
        Pixel List Builder

        Given a starting value for the first pixel in the first dimension, this function gets the pixel values
        in an array similar to a call to "get_row_pixels" or "get_column_pixels" for a puzzle piece.

        Args:
            start_value (int): Value of the first (i.e. lowest valued) pixel's first dimension

            is_row (bool): True if building a pixel list for a row and "False" if it is a column.  This is used to
            determine the stepping factor from one pixel to the next.

            reverse_list (bool): If "True", HIGHEST valued pixel dimension is returned in the first index of the list
            and all subsequent pixel values are monotonically DECREASING.  If "False", the LOWEST valued pixel dimension
            is returned in the first index of the list and all subsequent pixel values are monotonically increasing.

        Returns ([int]): An array of individual values simulating a set of pixels
        """

        # Determine the pixel to pixel step size
        if is_row:
            pixel_offset = PuzzleTester.NUMB_PIXEL_DIMENSIONS
        else:
            pixel_offset = PuzzleTester.row_to_row_step_size()

        # Build the list of pixel values
        pixels = numpy.zeros((PuzzleTester.PIECE_WIDTH, PuzzleTester.NUMB_PIXEL_DIMENSIONS))
        for i in range(0, PuzzleTester.PIECE_WIDTH):
            pixel_start = start_value + i * pixel_offset
            for j in range(0, PuzzleTester.NUMB_PIXEL_DIMENSIONS):
                pixels[i, j] = pixel_start + j

        # Return the result either reversed or not.
        if reverse_list:
            return pixels[::-1]
        else:
            return pixels

    @staticmethod
    def row_to_row_step_size():
        """
        Row to Row Step Size

        For a given pixel's given dimension, this function returns the number of dimensions between this pixel and
        the matching pixel exactly one row below.

        It is essentially the number of dimensions multiplied by the width of the original image (in pixels).

        Returns (int): Offset in dimensions.
        """
        step_size = PuzzleTester.NUMB_PIXEL_DIMENSIONS * PuzzleTester.PIECE_WIDTH * math.sqrt(PuzzleTester.NUMB_PUZZLE_PIECES)
        return int(step_size)

    @staticmethod
    def piece_to_piece_step_size():
        """
        Piece to Piece Step Size

        For a given pixel's given dimension, this function returns the number of dimensions between this pixel and
        the matching pixel exactly one puzzle piece away.

        It is essentially the number of dimensions multiplied by the width of a puzzle piece (in pixels).

        Returns (int): Offset in dimensions.
        """
        return PuzzleTester.NUMB_PIXEL_DIMENSIONS * PuzzleTester.PIECE_WIDTH

    @staticmethod
    def build_dummy_puzzle():
        """
        Dummy Puzzle Builder

        Using an image on the disk, this function builds a dummy puzzle using a Numpy array that is manually
        loaded with sequentially increasing pixel values.

        Returns (Puzzle): A puzzle where each pixel dimension from left to right sequentially increases by
        one.
        """

        # Create a puzzle whose image data will be overridden
        puzzle = Puzzle(0, PuzzleTester.TEST_IMAGE_FILENAME)

        # Define the puzzle side
        piece_width = PuzzleTester.PIECE_WIDTH
        numb_pieces = PuzzleTester.NUMB_PUZZLE_PIECES
        numb_dim = PuzzleTester.NUMB_PIXEL_DIMENSIONS

        # Define the array
        dummy_img = numpy.zeros((int(round(piece_width * math.sqrt(numb_pieces))),
                                 int(round(piece_width * math.sqrt(numb_pieces))),
                                 numb_dim))
        # populate the array
        val = PuzzleTester.TEST_ARRAY_FIRST_PIXEL_VALUE
        img_shape = dummy_img.shape
        for row in range(0, img_shape[0]):
            for col in range(0, img_shape[1]):
                for dim in range(0, img_shape[2]):
                    dummy_img[row, col, dim] = val
                    val += 1

        # Overwrite the image parameters
        puzzle._img = dummy_img
        puzzle._img_LAB = dummy_img
        puzzle._img_width = img_shape[1]
        puzzle._img_height = img_shape[0]
        puzzle._piece_width = PuzzleTester.PIECE_WIDTH
        puzzle._grid_size = (math.sqrt(PuzzleTester.NUMB_PUZZLE_PIECES), math.sqrt(PuzzleTester.NUMB_PUZZLE_PIECES))

        # Remake the puzzle pieces
        puzzle.make_pieces()
        return puzzle


if __name__ == "__main__":
    myPuzzle = Puzzle(0, ".\images\muffins_300x200.jpg")
    x = 1
