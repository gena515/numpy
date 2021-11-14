import os
import pytest
import textwrap
from numpy.testing import assert_array_equal
import numpy as np
from . import util


def _path(*a):
    return os.path.join(*((os.path.dirname(__file__),) + a))


class TestString(util.F2PyTest):
    sources = [_path('src', 'string', 'char.f90')]

    @pytest.mark.slow
    def test_char(self):
        strings = np.array(['ab', 'cd', 'ef'], dtype='c').T
        inp, out = self.module.char_test.change_strings(strings,
                                                        strings.shape[1])
        assert_array_equal(inp, strings)
        expected = strings.copy()
        expected[1, :] = 'AAA'
        assert_array_equal(out, expected)


class TestDocStringArguments(util.F2PyTest):
    suffix = '.f'

    code = """
C FILE: STRING.F
      SUBROUTINE FOO(A,B,C,D)
      CHARACTER*5 A, B
      CHARACTER*(*) C,D
Cf2py intent(in) a,c
Cf2py intent(inout) b,d
      ! PRINT*, "A=",A
      ! PRINT*, "B=",B
      ! PRINT*, "C=",C
      ! PRINT*, "D=",D
      ! PRINT*, "CHANGE A,B,C,D"
      A(1:1) = 'A'
      B(1:1) = 'B'
      C(1:1) = 'C'
      D(1:1) = 'D'
      ! PRINT*, "A=",A
      ! PRINT*, "B=",B
      ! PRINT*, "C=",C
      ! PRINT*, "D=",D
      END
C END OF FILE STRING.F
        """

    def test_example(self):
        a = np.array(b'123\0\0')
        b = np.array(b'123\0\0')
        c = np.array(b'123')
        d = np.array(b'123')

        self.module.foo(a, b, c, d)

        assert a.tobytes() == b'123\0\0'
        assert b.tobytes() == b'B23\0\0', (b.tobytes(),)
        assert c.tobytes() == b'123'
        assert d.tobytes() == b'D23'


class TestFixedString(util.F2PyTest):
    suffix = '.f90'

    code = textwrap.dedent("""
       function sint(s) result(i)
          implicit none
          character(len=*) :: s
          integer :: j, i
          i = 0
          do j=len(s), 1, -1
           if (.not.((i.eq.0).and.(s(j:j).eq.' '))) then
             i = i + ichar(s(j:j)) * 10 ** (j - 1)
           endif
          end do
          return
        end function sint

        function test_in_bytes4(a) result (i)
          implicit none
          integer :: sint
          character(len=4) :: a
          integer :: i
          i = sint(a)
          a(1:1) = 'A'
          return
        end function test_in_bytes4

        function test_inout_bytes4(a) result (i)
          implicit none
          integer :: sint
          character(len=4), intent(inout) :: a
          integer :: i
          if (a(1:1).ne.' ') then
            a(1:1) = 'E'
          endif
          i = sint(a)
          return
        end function test_inout_bytes4
        """)

    @staticmethod
    def _sint(s, start=0, end=None):
        """Return the content of a string buffer as integer value.

        For example:
          _sint('1234') -> 4321
          _sint('123A') -> 17321
        """
        if isinstance(s, np.ndarray):
            s = s.tobytes()
        elif isinstance(s, str):
            s = s.encode()
        assert isinstance(s, bytes)
        if end is None:
            end = len(s)
        i = 0
        for j in range(start, min(end, len(s))):
            i += s[j] * 10 ** j
        return i

    def _get_input(self, intent='in'):
        if intent in ['in']:
            yield ''
            yield '1'
            yield '1234'
            yield '12345'
            yield b''
            yield b'\0'
            yield b'1'
            yield b'\01'
            yield b'1\0'
            yield b'1234'
            yield b'12345'
        yield np.ndarray((), np.bytes_, buffer=b'')  # array(b'', dtype='|S0')
        yield np.array(b'')                          # array(b'', dtype='|S1')
        yield np.array(b'\0')
        yield np.array(b'1')
        yield np.array(b'1\0')
        yield np.array(b'\01')
        yield np.array(b'1234')
        yield np.array(b'123\0')
        yield np.array(b'12345')

    def test_intent_in(self):
        for s in self._get_input():
            r = self.module.test_in_bytes4(s)
            # also checks that s is not changed inplace
            expected = self._sint(s, end=4)
            assert r == expected, (s)

    def test_intent_inout(self):
        for s in self._get_input(intent='inout'):
            rest = self._sint(s, start=4)
            r = self.module.test_inout_bytes4(s)
            expected = self._sint(s, end=4)
            assert r == expected

            # check that the rest of input string is preserved
            assert rest == self._sint(s, start=4)
