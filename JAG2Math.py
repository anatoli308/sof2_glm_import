# ##### BEGIN GPL LICENSE BLOCK #####
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software Foundation,
#  Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import struct
from typing import BinaryIO
import mathutils

# 3 * 4 : shear not used.


class Matrix:
    def __init__(self):
        self.rows = []
        for i in range(3):
            self.rows.append([0, 0, 0, 0])
        self.rows[0][0] = 1
        self.rows[1][1] = 1
        self.rows[2][2] = 1

    def loadFromFile(self, file: BinaryIO) -> None:
        for y in range(3):
            for x in range(4):
                self.rows[y][x], = struct.unpack("f", file.read(4))

    def saveToFile(self, file: BinaryIO) -> None:
        for y in range(3):
            for x in range(4):
                file.write(struct.pack("f", self.rows[y][x]))

    def toBlender(self) -> mathutils.Matrix:
        mat = mathutils.Matrix(
            [self.rows[0], self.rows[1], self.rows[2], [0, 0, 0, 1]])
        return mat

    def fromBlender(self, mat: mathutils.Matrix) -> None:
        mat = mathutils.Matrix(mat)
        mat.to_4x4()
        self.rows = []
        for row in mat:
            l = []
            l.extend(row)
            self.rows.append(l)
        del self.rows[3]


def GLABoneRotToBlender(matrix: mathutils.Matrix) -> None:
    """
    Changes a GLA bone's rotation matrix (X+ = front) to blender style (Y+ = front)
    """
    new_x = -matrix.col[1].copy()
    new_y = matrix.col[0].copy()
    matrix.col[0] = new_x
    matrix.col[1] = new_y
    # undo change in translation
    matrix[3][0], matrix[3][1] = matrix[3][1], -matrix[3][0]

    # also, roll 90 degrees
    matrix[0][0], matrix[1][0], matrix[2][0], matrix[0][2], matrix[1][2], matrix[2][2] = - \
        matrix[0][2], -matrix[1][2], - \
        matrix[2][2], matrix[0][0], matrix[1][0], matrix[2][0]


def BlenderBoneRotToGLA(matrix: mathutils.Matrix) -> None:
    """
    Changes a blender bone's rotation matrix (Y+ = front) to GLA style (X+ = front)
    """
    # undo roll 90 degrees
    matrix[0][0], matrix[1][0], matrix[2][0], matrix[0][2], matrix[1][2], matrix[2][2] = matrix[0][2], matrix[1][2], matrix[2][2], - \
        matrix[0][0], -matrix[1][0], -matrix[2][0]

    new_x = matrix.col[1].copy()
    new_y = -matrix.col[0].copy()
    matrix.col[0] = new_x
    matrix.col[1] = new_y
    # undo change in translation
    matrix[3][0], matrix[3][1] = matrix[3][1], -matrix[3][0]

# compressed bones as used in GLA files


class CompBone:
    def __init__(self, matrix: mathutils.Matrix):
        self.matrix = matrix

    @staticmethod
    def loadFromFile(file: BinaryIO) -> "CompBone":
        quat = mathutils.Quaternion()
        loc = mathutils.Vector([0, 0, 0, 1])  # make sure it's 4 dimensional
        # 14 bytes: 4 shorts for quat = 8 bytes, 3 shorts for position = 6 bytes
        q_w, q_x, q_y, q_z, l_x, l_y, l_z = struct.unpack("7H", file.read(14))
        # map quaternion values from 0..65535 to -2..2
        quat.w = (q_w / 16383) - 2
        quat.x = (q_x / 16383) - 2
        quat.y = (q_y / 16383) - 2
        quat.z = (q_z / 16383) - 2
        # map location from 0..65535 to -512..512 (511.984375)
        loc.x = (l_x / 64) - 512
        loc.y = (l_y / 64) - 512
        loc.z = (l_z / 64) - 512

        # turn rotation into matrix
        matrix = quat.to_matrix()
        # resize to 4x4 so we can add translation
        matrix.resize_4x4()
        # add translation
        matrix.col[3] = loc
        assert (matrix[3][3] == 1)
        # convert to blender style
        # shouldn't be done until all offsets have been combined.
        # GLABoneRotToBlender(self.matrix)

        return CompBone(matrix)

    # returns the 14 byte compressed representation of this matrix (no scale) as saved in the compBonePool
    @staticmethod
    def compress(mat: mathutils.Matrix) -> bytes:
        loc = mat.to_translation()
        quat = mat.to_quaternion()
        return struct.pack("7H",
                           round((quat.w + 2) * 16383),
                           round((quat.x + 2) * 16383),
                           round((quat.y + 2) * 16383),
                           round((quat.z + 2) * 16383),
                           round((loc.x + 512) * 64),
                           round((loc.y + 512) * 64),
                           round((loc.z + 512) * 64))
