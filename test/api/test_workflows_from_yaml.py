from __future__ import print_function

import json
import os

from base.populators import uses_test_history
from base.workflow_fixtures import (
    WORKFLOW_RUNTIME_PARAMETER_SIMPLE,
    WORKFLOW_SIMPLE_CAT_AND_RANDOM_LINES,
    WORKFLOW_SIMPLE_CAT_TWICE,
    WORKFLOW_WITH_OUTPUT_ACTIONS,
    WORKFLOW_WITH_OUTPUTS
)

from .test_workflows import BaseWorkflowsApiTestCase

WORKFLOWS_DIRECTORY = os.path.abspath(os.path.dirname(__file__))


class WorkflowsFromYamlApiTestCase(BaseWorkflowsApiTestCase):

    def setUp(self):
        super(WorkflowsFromYamlApiTestCase, self).setUp()

    def _upload_and_download(self, yaml_workflow):
        workflow_id = self._upload_yaml_workflow(yaml_workflow)
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        return workflow

    def test_simple_upload(self):
        workflow = self._upload_and_download(WORKFLOW_SIMPLE_CAT_AND_RANDOM_LINES)

        tool_count = {'random_lines1': 0, 'cat1': 0}
        input_found = False
        for step in workflow['steps'].values():
            step_type = step['type']
            if step_type == "data_input":
                assert step['label'] == 'the_input'
                input_found = True
            else:
                tool_id = step['tool_id']
                tool_count[tool_id] += 1
                if tool_id == "random_lines1":
                    assert step['label'] == "random_line_label"

        assert input_found
        assert tool_count['random_lines1'] == 1
        assert tool_count['cat1'] == 2

# FIXME:  This test fails on some machines due to (we're guessing) yaml.safe_loading
# order being not guaranteed and inconsistent across platforms.  The workflow
# yaml.safe_loader probably needs to enforce order using something like the
# approach described here:
# https://stackoverflow.com/questions/13297744/pyyaml-control-ordering-of-items-called-by-yaml.safe_load
#     def test_multiple_input( self ):
#         history_id = self.dataset_populator.new_history()
#         self._run_jobs("""
# steps:
#   - type: input
#     label: input1
#   - type: input
#     label: input2
#   - tool_id: cat_list
#     state:
#       input1:
#       - $link: input1
#       - $link: input2
# test_data:
#   input1: "hello world"
#   input2: "123"
# """, history_id=history_id)
#         contents1 = self.dataset_populator.get_history_dataset_content(history_id)
#         assert contents1 == "hello world\n123\n"

    def test_simple_output_actions(self):
        history_id = self.dataset_populator.new_history()
        self._run_jobs(WORKFLOW_WITH_OUTPUT_ACTIONS, test_data="""
input1: "hello world"
""", history_id=history_id)

        details1 = self.dataset_populator.get_history_dataset_details(history_id, hid=2)
        assert not details1["visible"]
        assert details1["name"] == "the new value", details1
        details2 = self.dataset_populator.get_history_dataset_details(history_id, hid=3)
        assert details2["visible"]

    def test_inputs_to_steps(self):
        history_id = self.dataset_populator.new_history()
        self._run_jobs(WORKFLOW_SIMPLE_CAT_TWICE, test_data={"input1": "hello world"}, history_id=history_id)
        contents1 = self.dataset_populator.get_history_dataset_content(history_id)
        self.assertEqual(contents1.strip(), "hello world\nhello world")

    def test_outputs(self):
        workflow_id = self._upload_yaml_workflow(WORKFLOW_WITH_OUTPUTS)
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        self.assertEqual(workflow["steps"]["1"]["workflow_outputs"][0]["output_name"], "out_file1")
        self.assertEqual(workflow["steps"]["1"]["workflow_outputs"][0]["label"], "wf_output_1")

    def test_runtime_inputs(self):
        workflow = self._upload_and_download(WORKFLOW_RUNTIME_PARAMETER_SIMPLE)
        assert len(workflow["steps"]) == 2
        runtime_step = workflow["steps"]["1"]
        for runtime_input in runtime_step["inputs"]:
            if runtime_input["name"] == "num_lines":
                break

        assert runtime_input["description"].startswith("runtime parameter for tool")

        tool_state = json.loads(runtime_step["tool_state"])
        assert "num_lines" in tool_state
        self._assert_is_runtime_input(tool_state["num_lines"])

    def test_subworkflow_simple(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
inputs:
  outer_input: data
steps:
  - tool_id: cat1
    label: first_cat
    in:
      input1: outer_input
  - run:
      class: GalaxyWorkflow
      inputs:
        inner_input: data
      steps:
        - tool_id: random_lines1
          state:
            num_lines: 1
            input:
              $link: inner_input
            seed_source:
              seed_source_selector: set_seed
              seed: asdf
    label: nested_workflow
    in:
      inner_input: first_cat/out_file1

test_data:
  outer_input:
    value: 1.bed
    type: File
""")
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        by_label = self._steps_by_label(workflow)
        if "nested_workflow" not in by_label:
            template = "Workflow [%s] does not contain label 'nested_workflow'."
            message = template % workflow
            raise AssertionError(message)

        subworkflow_step = by_label["nested_workflow"]
        assert subworkflow_step["type"] == "subworkflow"
        assert len(subworkflow_step["subworkflow"]["steps"]) == 2

        subworkflow_connections = subworkflow_step["input_connections"]
        assert len(subworkflow_connections) == 1
        subworkflow_connection = subworkflow_connections["inner_input"]
        assert subworkflow_connection["input_subworkflow_step_id"] == 0

        workflow_reupload_id = self.import_workflow(workflow)["id"]
        workflow_reupload = self._get("workflows/%s/download" % workflow_reupload_id).json()
        by_label = self._steps_by_label(workflow_reupload)
        subworkflow_step = by_label["nested_workflow"]
        assert subworkflow_step["type"] == "subworkflow"
        assert len(subworkflow_step["subworkflow"]["steps"]) == 2

        subworkflow_connections = subworkflow_step["input_connections"]
        assert len(subworkflow_connections) == 1
        subworkflow_connection = subworkflow_connections["inner_input"]
        assert subworkflow_connection["input_subworkflow_step_id"] == 0

        # content = self.dataset_populator.get_history_dataset_content( history_id )
        # self.assertEqual("chr5\t131424298\t131424460\tCCDS4149.1_cds_0_0_chr5_131424299_f\t0\t+\n", content)

    def test_pause(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  - label: test_input
    type: input
  - label: first_cat
    tool_id: cat1
    state:
      input1:
        $link: test_input
  - label: the_pause
    type: pause
    in:
      input: first_cat/out_file1
  - label: second_cat
    tool_id: cat1
    in:
      input1: the_pause
""")
        print(self._get("workflows/%s/download" % workflow_id).json())

    def test_implicit_connections(self):
        workflow_id = self._upload_yaml_workflow("""
class: GalaxyWorkflow
steps:
  - label: test_input
    type: input
  - label: first_cat
    tool_id: cat1
    state:
      input1:
        $link: test_input
  - label: the_pause
    type: pause
    connect:
      input:
      - first_cat#out_file1
  - label: second_cat
    tool_id: cat1
    state:
      input1:
        $link: the_pause
  - label: third_cat
    tool_id: cat1
    connect:
      $step: second_cat
    state:
      input1:
        $link: test_input
""")
        workflow = self._get("workflows/%s/download" % workflow_id).json()
        print(workflow)

    @uses_test_history()
    def test_conditional_ints(self, history_id):
        self._run_jobs("""
class: GalaxyWorkflow
steps:
  - label: test_input
    tool_id: disambiguate_cond
    state:
      p3:
        use: true
      files:
        attach_files: false
""", test_data={}, history_id=history_id)
        content = self.dataset_populator.get_history_dataset_content(history_id)
        assert "no file specified" in content
        assert "7 7 4" in content

        self._run_jobs("""
class: GalaxyWorkflow
steps:
  - label: test_input
    tool_id: disambiguate_cond
    state:
      p3:
        use: true
        p3v: 5
      files:
        attach_files: false
""", test_data={}, history_id=history_id)
        content = self.dataset_populator.get_history_dataset_content(history_id)
        assert "no file specified" in content
        assert "7 7 5" in content

    def _steps_by_label(self, workflow_as_dict):
        by_label = {}
        assert "steps" in workflow_as_dict, workflow_as_dict
        for step in workflow_as_dict["steps"].values():
            by_label[step['label']] = step
        return by_label
