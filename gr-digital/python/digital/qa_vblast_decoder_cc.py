#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2018 Free Software Foundation, Inc.
# 
# This file is part of GNU Radio
# 
# GNU Radio is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 3, or (at your option)
# any later version.
# 
# GNU Radio is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with GNU Radio; see the file COPYING.  If not, write to
# the Free Software Foundation, Inc., 51 Franklin Street,
# Boston, MA 02110-1301, USA.
# 

from gnuradio import gr, gr_unittest
from gnuradio import blocks
import digital_swig as digital
import numpy as np
import pmt

class qa_vblast_decoder_cc (gr_unittest.TestCase):

    def setUp (self):
        self.tb = gr.top_block ()

    def tearDown (self):
        self.tb = None

    def dice_csi_tags(self, data, type, num_inputs, num_tags, tag_pos, vlen=1):
        tags = []
        expected_result = np.empty([np.size(data, 0)*np.size(data,1)], dtype=complex)

        if type == 'MMSE':
            # Add an SNR tag at the start of the stream for MMSE.
            tags.append(gr.tag_utils.python_to_tag((0,
                                                    pmt.string_to_symbol("snr"),
                                                    pmt.make_f32vector(num_inputs, 1e8),
                                                    pmt.from_long(0))))

        for i in range(0, num_tags):
            # Randomly generate CSI for one symbol.
            csi = (np.random.randn(vlen, num_inputs, num_inputs) + 1j * np.random.randn(vlen, num_inputs, num_inputs))
            # Assign the CSI vector to a PMT vector.
            csi_pmt = pmt.make_vector(vlen, pmt.make_vector(num_inputs, pmt.make_c32vector(num_inputs, 1.0)))
            for k, carrier in enumerate(csi):
                carrier_vector_pmt = pmt.make_vector(num_inputs, pmt.make_c32vector(num_inputs, csi[k][0][0]))
                for l, rx in enumerate(csi[k]):
                    line_vector_pmt = pmt.make_c32vector(num_inputs, csi[k][l][0])
                    for m, tx in enumerate(csi[k][l]):
                        pmt.c32vector_set(v=line_vector_pmt, k=m, x=csi[k][l][m])
                    pmt.vector_set(carrier_vector_pmt, l, line_vector_pmt)
                pmt.vector_set(csi_pmt, k, carrier_vector_pmt)

            # Append stream tags with CSI to data stream.
            tags.append(gr.tag_utils.python_to_tag((tag_pos[i],
                                                    pmt.string_to_symbol("csi"),
                                                    csi_pmt,
                                                    pmt.from_long(0))))

            # Calculate expected result.
            expected_result[tag_pos[i]*num_inputs::] = np.reshape(np.transpose(np.dot(np.linalg.inv(csi), data[::, tag_pos[i]::])), (np.size(data, 0)*(np.size(data,1)-tag_pos[i])))
        return tags, expected_result

    def build_and_run_flowgraph(self, repetitions, data_length, num_inputs_min, num_inputs_max, num_tags, equalizer_type):
        for i in range(repetitions):
            # Generate random number of inputs.
            num_inputs = np.random.randint(low=num_inputs_min, high=num_inputs_max+1)
            # Generate random input data.
            data = np.random.randn(num_inputs, data_length) + 1j * np.random.randn(num_inputs, data_length)
            # Generate random tag positions.
            tag_pos = np.random.randint(low=0, high=data_length, size=num_tags)
            tag_pos[0] = 0
            tag_pos = np.sort(tag_pos)
            # Calculate expected result.
            tags, expected_result = self.dice_csi_tags(data,
                                                       equalizer_type,
                                                       num_inputs,
                                                       num_tags,
                                                       tag_pos)

            # Build up the test flowgraph.
            src = []
            src.append(blocks.vector_source_c(data=data[0],
                                              repeat=False,
                                              tags=tags))
            for n in range(1, num_inputs):
                src.append(blocks.vector_source_c(data=data[n],
                                                  repeat=False))
            vblast_decoder = digital.vblast_decoder_cc(num_inputs, equalizer_type)
            sink = blocks.vector_sink_c()
            self.tb.connect(src[0], vblast_decoder, sink)
            for n in range(1, num_inputs):
                self.tb.connect(src[n], (vblast_decoder, n))
            # Run flowgraph.
            self.tb.run()

            # Check if the expected result equals the actual result.
            self.assertComplexTuplesAlmostEqual(expected_result, sink.data(), 2)

    ''' 
    2 tests validating the correct output of the decoder with random input data, ZF equalizer
    and 1x1 MIMO scheme. '''
    def test_001_t(self):
        self.build_and_run_flowgraph(repetitions=2,
                                     data_length=10,
                                     num_inputs_min=1,
                                     num_inputs_max=1,
                                     num_tags=4,
                                     equalizer_type='ZF')

    ''' 
    2 tests validating the correct output of the decoder with random input data, MMSE equalizer
    and 1x1 MIMO scheme. '''
    def test_002_t(self):
        self.build_and_run_flowgraph(repetitions=2,
                                     data_length=10,
                                     num_inputs_min=1,
                                     num_inputs_max=1,
                                     num_tags=4,
                                     equalizer_type='MMSE')

    ''' 
    2 tests validating the correct output of the decoder with random input data, ZF equalizer
    and 2x2 MIMO scheme. '''
    def test_003_t(self):
        self.build_and_run_flowgraph(repetitions=2,
                                     data_length=10,
                                     num_inputs_min=2,
                                     num_inputs_max=2,
                                     num_tags=4,
                                     equalizer_type='ZF')

    ''' 
    2 tests validating the correct output of the decoder with random input data, MMSE equalizer
    and 2x2 MIMO scheme and an extremely high SNR regime (1/snr -> 0). '''
    def test_004_t(self):
        self.build_and_run_flowgraph(repetitions=2,
                                     data_length=10,
                                     num_inputs_min=2,
                                     num_inputs_max=2,
                                     num_tags=4,
                                     equalizer_type='MMSE')

    ''' 
    2 tests validating the correct output of the decoder with random input data, ZF equalizer
    and MxM MIMO scheme with M in [3, 16]. '''
    def test_005_t(self):
        self.build_and_run_flowgraph(repetitions=2,
                                     data_length=10,
                                     num_inputs_min=3,
                                     num_inputs_max=16,
                                     num_tags=4,
                                     equalizer_type='ZF')

    ''' 
    2 tests validating the correct output of the decoder with random input data, MMSE equalizer
    and MxM MIMO scheme with M in [3, 16]. '''

    def test_006_t(self):
        self.build_and_run_flowgraph(repetitions=2,
                                     data_length=10,
                                     num_inputs_min=3,
                                     num_inputs_max=16,
                                     num_tags=4,
                                     equalizer_type='MMSE')

if __name__ == '__main__':
    gr_unittest.run(qa_vblast_decoder_cc, "qa_vblast_decoder_cc.xml")
