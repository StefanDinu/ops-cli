# Copyright 2019 Adobe. All rights reserved.
# This file is licensed to you under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License. You may obtain a copy
# of the License at http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software distributed under
# the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR REPRESENTATIONS
# OF ANY KIND, either express or implied. See the License for the specific language
# governing permissions and limitations under the License.

from config_generator import ConfigProcessor

from ops import Executor
import logging
import os

logger = logging.getLogger(__name__)


class CompositionConfigGenerator:

    def __init__(self, composition_order):
        self.composition_sorter = CompositionSorter(composition_order)
        self.generator = ConfigProcessor()

    def get_sorted_compositions(self, path, reverse=False):
        all_compositions = self.discover_all_compositions(path)
        compositions = self.sort_compositions(all_compositions, reverse)
        return compositions

    def discover_all_compositions(self, path):
        path_params = dict(self.split_path(x) for x in path.split('/'))

        composition = path_params.get("composition", None)
        if composition:
            return [composition]

        return self.get_compositions_in_path(path)

    def get_compositions_in_path(self, path):
        compositions = []
        subpaths = os.listdir(path)
        for subpath in subpaths:
            if "composition=" in subpath:
                composition = self.split_path(subpath)[1]
                compositions.append(composition)
        return compositions

    def run_sh(self, command, cwd=None, exit_on_error=True):
        args = {"command": command}
        execute = Executor()
        exit_code = execute(args, cwd=cwd)
        if exit_code != 0:
            logger.error("Command finished with non zero exit code.")
            if exit_on_error:
                exit(exit_code)

    def split_path(self, value, separator='='):
        if separator in value:
            return value.split(separator)
        return [value, ""]

    def sort_compositions(self, all_compositions, reverse=False):
        return self.composition_sorter.get_sorted_compositions(all_compositions, reverse)

    def get_config_path_for_composition(self, path_prefix, composition):
        prefix = os.path.join(path_prefix, '')
        return path_prefix if "composition=" in path_prefix else "{}composition={}".format(prefix, composition)

    def get_terraform_path_for_composition(self, path_prefix, composition):
        prefix = os.path.join(path_prefix, '')
        return path_prefix if composition in path_prefix else "{}{}/".format(prefix, composition)

class TerraformConfigGenerator(CompositionConfigGenerator, object):

    def __init__(self, composition_order):
        super(TerraformConfigGenerator, self).__init__(composition_order)

    def generate_files(self, config_path, composition_path, composition):
        config_path = self.get_config_path_for_composition(config_path, composition)
        composition_path = self.get_terraform_path_for_composition(composition_path, composition)
        self.generate_provider_config(config_path, composition_path)
        self.generate_variables_config(config_path, composition_path)

    def generate_provider_config(self, config_path, composition_path):
        output_file = "{}provider.tf.json".format(composition_path)
        logger.info('Generating terraform config %s', output_file)
        self.generator.process(path=config_path,
                               filters=["provider", "terraform"],
                               output_format="json",
                               output_file=output_file,
                               skip_interpolation_validation=True,
                               print_data=True)

    def generate_variables_config(self, config_path, composition_path):
        output_file = "{}variables.tfvars.json".format(composition_path)
        logger.info('Generating terraform config %s', output_file)
        self.generator.process(path=config_path,
                               exclude_keys=["helm", "provider"],
                               enclosing_key="config",
                               output_format="json",
                               output_file=output_file,

                               # skip validation, since some interpolations might not be able to be resolved
                               # at this point (eg. {{outputs.*}}, which reads from a terraform state file
                               # that might not yet be created)
                               skip_interpolation_validation=True,
                               print_data=True)


class CompositionSorter(object):
    def __init__(self, composition_order):
        self.composition_order = composition_order

    def get_sorted_compositions(self, compositions, reverse=False):
        result = filter(lambda x: x in compositions, self.composition_order)
        return tuple(reversed(result)) if reverse else result

