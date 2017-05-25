#
# eChronos Real-Time Operating System
# Copyright (C) 2015  National ICT Australia Limited (NICTA), ABN 62 102 206 173.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, version 3, provided that these additional
# terms apply under section 7:
#
#   No right, title or interest in or to any trade mark, service mark, logo or
#   trade name of of National ICT Australia Limited, ABN 62 102 206 173
#   ("NICTA") or its licensors is granted. Modified versions of the Program
#   must be plainly marked as such, and must not be distributed using
#   "eChronos" as a trade mark or product name, or misrepresented as being the
#   original Program.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# @TAG(NICTA_AGPL)
#
# pylint: disable=protected-access
import itertools
import os
import tempfile
import unittest
from pylib.utils import BASE_DIR
from pylib.components import _sort_typedefs, _sort_by_dependencies, _DependencyNode, _UnresolvableDependencyError
from pylib.task import _Review, Task, _InvalidTaskStateError, TaskConfiguration
from pylib.task_commands import TASK_CFG


class TestCase(unittest.TestCase):
    def test_empty(self):
        """Test whether an empty test can be run at all given the test setup in x.py."""
        pass

    def test_sort_typedefs(self):
        typedefs = ['typedef uint8_t foo;',
                    'typedef foo bar;',
                    'typedef bar baz;']
        expected = '\n'.join(typedefs)
        for permutation in itertools.permutations(typedefs):
            self.assertEqual(_sort_typedefs('\n'.join(permutation)), expected)

    def test_full_stop_in_reviewer_name(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            round_ = 0
            author = 'john.doe'
            review_file_path = os.path.join(temp_dir, '{}.{}.md'.format(author, round_))
            open(review_file_path, 'w').close()
            review = _Review(review_file_path)
            self.assertEqual(review.author, author)
            self.assertEqual(review.round, round_)

    def test_resolve_dependencies(self):
        node_a = _DependencyNode(('a',), ('b', 'c'))
        node_b = _DependencyNode(('b',), ('c',))
        node_c = _DependencyNode(('c',), ())
        nodes = (node_a, node_b, node_c)
        output = list(_sort_by_dependencies(nodes))
        self.assertEqual(output, [node_c, node_b, node_a])

    def test_resolve_unresolvable_dependencies(self):
        node_a = _DependencyNode(('a',), ('b',))
        node_b = _DependencyNode(('b',), ('c',))
        nodes = (node_a, node_b)

        def test_func(nds):
            list(_sort_by_dependencies(nds))

        self.assertRaises(_UnresolvableDependencyError, test_func, nodes)

    def test_resolve_cyclic_dependencies(self):
        node_a = _DependencyNode(('a',), ())
        node_b = _DependencyNode(('b',), ('a',))
        node_c = _DependencyNode(('c',), ('b', 'd'))
        node_d = _DependencyNode(('d',), ('c',))
        nodes = (node_a, node_b, node_c, node_d)

        def test_func(nds):
            list(_sort_by_dependencies(nds))

        self.assertRaises(_UnresolvableDependencyError, test_func, nodes)
        output = list(_sort_by_dependencies(nodes, ignore_cyclic_dependencies=True))
        self.assertEqual(sorted(output), sorted(nodes))

    @unittest.skipUnless(os.path.isdir(os.path.join(BASE_DIR, '.git')), 'Test depends on valid git repo')
    def test_task_accepted(self):  # pylint: disable=no-self-use
        # This task was accepted without any rework reviews
        task_dummy_create("test_task_accepted")._check_is_accepted()

    @unittest.skipUnless(os.path.isdir(os.path.join(BASE_DIR, '.git')), 'Test depends on valid git repo')
    def test_rework_is_accepted(self):  # pylint: disable=no-self-use
        # This task had a rework review that was later accepted by its review author
        task_dummy_create("test_rework_is_accepted")._check_is_accepted()

    @unittest.skipUnless(os.path.isdir(os.path.join(BASE_DIR, '.git')), 'Test depends on valid git repo')
    def test_rework_not_accepted(self):
        # This task was erroneously integrated with a rework review not later accepted by its review author
        task = task_dummy_create("test_rework_not_accepted")
        self.assertRaises(_InvalidTaskStateError, task._check_is_accepted)

    @unittest.skipUnless(os.path.isdir(os.path.join(BASE_DIR, '.git')), 'Test depends on valid git repo')
    def test_not_enough_accepted(self):
        # This task was integrated after being accepted by only one reviewer
        # before we placed a hard minimum in the check
        task = task_dummy_create("test_not_enough_accepted")
        self.assertRaises(_InvalidTaskStateError, task._check_is_accepted)


# Helper for the pre-integration check tests
def task_dummy_create(task_name):
    cfg = TaskConfiguration(repo_path=BASE_DIR,
                            tasks_path=os.path.join('x_test_data', 'tasks'),
                            description_template_path=TASK_CFG.description_template_path,
                            reviews_path=os.path.join('x_test_data', 'reviews'),
                            mainline_branch=TASK_CFG.mainline_branch)
    return Task(cfg, task_name, checkout=False)
