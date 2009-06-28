"""
Integration tests of mlab with the null engine.

This also tests some numerics with VTK.
"""

import unittest

import numpy as np

from enthought.mayavi import mlab
from enthought.mayavi.core.null_engine import NullEngine
from enthought.tvtk.api import tvtk
from enthought.mayavi.tools.engine_manager import engine_manager
from enthought.mayavi.core.registry import registry


################################################################################
# class `TestMlabNullEngine`
################################################################################
class TestMlabNullEngine(unittest.TestCase):
    """ Stub mlab to isolate as well as possible from creation of a new
        figure.
    """

    def setUp(self):
        mlab.options.backend = 'test'
        e = NullEngine()
        e.start()
        mlab.set_engine(e)
        self.e = e

    def tearDown(self):
        # Check that the NullEngine is still the mlab engine 
        if not mlab.get_engine() is self.e:
            raise AssertionError, \
                    "The NullEngine has been overridden"
        engine_manager.current_engine = None
        # Unregistering the engine, to avoid side-effects between tests
        self.e.stop()
        registry.unregister_engine(self.e)
 

################################################################################
# class `TestMlabNullEngineMisc`
################################################################################
class TestMlabNullEngineMisc(TestMlabNullEngine):
    """ Misc tests for mlab with the null engine
    """
    def test_contour_filter(self):
        a = np.zeros((3, 3, 3))
        a[1, 1, 1] = 1

        src = mlab.pipeline.scalar_field(a)
        filter = mlab.pipeline.contour(src)

        x, y, z = filter.outputs[0].points.to_array().T

        # Check that the contour filter indeed did its work:
        np.testing.assert_almost_equal(x, [ 2. ,  2. ,  1.5,  2.5,  2. ,  2. ])
        np.testing.assert_almost_equal(y, [ 2. ,  1.5,  2. ,  2. ,  2.5,  2. ])
        np.testing.assert_almost_equal(z, [ 1.5,  2. ,  2. ,  2. ,  2. ,  2.5])

        # Check that the filter was not added to a live scene:
        if filter.scene is not None:
            raise AssertionError, "The NullEngine seems not to work"

    def test_user_defined_filter(self):
        x, y, z = np.random.random((3, 100))
        src = mlab.pipeline.scalar_scatter(x, y, z)
        density = mlab.pipeline.user_defined(src, filter='GaussianSplatter')

        self.assertEqual(len(density.outputs), 1)
        self.assert_(isinstance(density.outputs[0], tvtk.ImageData))

    def test_mlab_source(self):
        """ Check that the different objects created by mlab have an 
            'mlab_source' attribute.
        """
        # Test for functions taking 3D scalar data
        pipelines = (
            (mlab.pipeline.scalar_scatter, ),
            (mlab.pipeline.scalar_field, ),
            (mlab.pipeline.scalar_field, mlab.pipeline.image_plane_widget),
            (mlab.contour3d, ),
            (mlab.points3d, ), )
        data = np.random.random((3, 3, 3))
        for pipeline in pipelines:
            obj = pipeline[0](data)
            for factory in pipeline[1:]:
                obj = factory(obj)
            self.assertTrue(hasattr(obj, 'mlab_source'))
        # Test for functions taking x, y, z 2d arrays.
        x, y, z = np.random.random((3, 3, 3))
        pipelines = (
            (mlab.mesh, ),
            (mlab.surf, ),
            (mlab.quiver3d, ),
            (mlab.pipeline.vector_scatter, ),
            (mlab.pipeline.vector_scatter,
                            mlab.pipeline.extract_vector_components),
            (mlab.pipeline.vector_scatter,
                            mlab.pipeline.extract_vector_norm),
            (mlab.pipeline.array2d_source, ), )
        for pipeline in pipelines:
            obj = pipeline[0](x, y, z)
            for factory in pipeline[1:]:
                obj = factory(obj)
            self.assertTrue(hasattr(obj, 'mlab_source'))


################################################################################
# class `TestMlabModules`
################################################################################
class TestMlabModules(TestMlabNullEngine):
    """ Test the mlab modules.
    """
    def test_volume(self):
        """ Test the mlab volume factory.
        """
        scalars = np.zeros((3, 3, 3))
        scalars[0] = 1
        src = mlab.pipeline.scalar_field(scalars)
        color = (1, 0.1, 0.314)
        vol = mlab.pipeline.volume(src, vmin=0.5, vmax=0.9, color=color)
        # Test the color feature
        for value in np.random.random(10):
            np.testing.assert_array_equal(vol._ctf.get_color(value),
                                            color)
        # Test the vmin and vmax features
        for value in 0.5*np.random.random(10):
            self.assertEqual(vol._otf.get_value(value), 0)
        for value in (0.9+0.1*np.random.random(10)):
            self.assertEqual(vol._otf.get_value(value), 0.2)
        # Test the rescaling of the colormap when using vmin and vmax
        # Rmq: we have to be careful: the range of the ctf can change
        vol1 = mlab.pipeline.volume(src)
        range1 = vol1._ctf.range[1] - vol1._ctf.range[0]
        vol2 = mlab.pipeline.volume(src, vmin=0.25, vmax=0.75)
        range2 = vol2._ctf.range[1] - vol2._ctf.range[0]
        for value in 0.5*np.random.random(10):
            np.testing.assert_array_almost_equal(
                        vol1._ctf.get_color(2*range1*value),
                        vol2._ctf.get_color(0.25+range2*value))
        # Test outside the special [0, 1] range        
        src = mlab.pipeline.scalar_field(2*scalars)
        vol1 = mlab.pipeline.volume(src)
        range1 = vol1._ctf.range[1] - vol1._ctf.range[0]
        vol2 = mlab.pipeline.volume(src, vmin=0.5, vmax=1.5)
        range2 = vol2._ctf.range[1] - vol2._ctf.range[0]
        for value in np.random.random(10):
            np.testing.assert_array_almost_equal(
                        vol1._ctf.get_color(2*range1*value),
                        vol2._ctf.get_color(0.5+range2*value))
        
    def test_text(self):
        """ Test the text module.
        """
        data = np.random.random((3, 3, 3))
        src = mlab.pipeline.scalar_field(data)
        # Some smoke testing
        mlab.text(0.1, 0.9, 'foo')
        mlab.text(3, 3, 'foo', z=3)
        mlab.title('foo')
        # Check that specifying 2D positions larger than 1 raises an
        # error
        self.assertRaises(ValueError, mlab.text, 0, 1.5, 'test')

    def test_text3d(self):
        """ Test the text3d module.
        """
        data = np.random.random((3, 3, 3))
        src = mlab.pipeline.scalar_field(data)
        t = mlab.text3d(0, 0, 0, 'foo', opacity=0.5, scale=2,
                    orient_to_camera=False, color=(0, 0, 0),
                    orientation=(90, 0, 0))

    def test_contour_grid_plane(self):
        """Test the contour_grid_plane.
        """
        data = np.random.random((10, 10, 10))
        src = mlab.pipeline.scalar_field(data)
        mlab.pipeline.outline(src)
        mlab.pipeline.grid_plane(src)
        mlab.pipeline.contour_grid_plane(src)

    def test_barchart(self):
        """Test the barchart function."""
            
        from numpy import random, abs
        s = np.abs(np.random.random((3,3)))
        b = mlab.barchart(s)
        self.assertEqual(b.glyph.glyph.scale_mode,
                         'scale_by_vector_components')
        s += 1
        b.mlab_source.update()
        self.assertEqual(b.glyph.glyph.scale_mode,
                         'scale_by_vector_components')


if __name__ == '__main__':
    unittest.main()

