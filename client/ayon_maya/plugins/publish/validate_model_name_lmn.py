import inspect
import os
import re
import ayon_maya.api.action
from ayon_core.pipeline.publish import (
    OptionalPyblishPluginMixin,
    PublishValidationError,
    ValidateContentsOrder,
)
from ayon_maya.api import lib
from ayon_maya.api import plugin
from maya import cmds


class ValidateModelNames(plugin.MayaInstancePlugin,
                         OptionalPyblishPluginMixin):

    optional = True
    order = ValidateContentsOrder
    families = ["model"]
    label = "Model Names"
    actions = [ayon_maya.api.action.SelectInvalidAction]

    @classmethod
    def get_shaders(cls):
        shaders = []

        ACACIA = os.environ.get("ACACIA")
        material_file = os.path.join(
            ACACIA, "hosts", "Maya", "presets", "shaders", "sh_simple_list.txt")

        if os.path.isfile(material_file):
            shader_file = open(material_file, "r")
            shaders = shader_file.readlines()
            shader_file.close()

        shaders = list(map(lambda s: s.rstrip(), shaders))  # Convert to list

        return shaders

    @classmethod
    def get_invalid(cls, instance):

        def is_group(group_name):
            """Find out if supplied transform is group or not."""
            try:
                children = cmds.listRelatives(group_name, children=True)
                for child in children:
                    if not cmds.ls(child, transforms=True):
                        return False
                return True
            except:
                return False
        invalid = []

        descendants = cmds.listRelatives(instance,
                                         allDescendents=True,
                                         fullPath=True) or []

        descendants = cmds.ls(descendants, noIntermediate=True, long=True)
        trns = cmds.ls(descendants, long=False, type='transform')

        # filter out groups
        filtered = [node for node in trns if not is_group(node)]

        shaders = cls.get_shaders()
        regex = "[\da-zA-Z]+_(?P<shader>[\da-zA-Z]+)_(GEO|MESH)"

        r = re.compile(regex)
        for obj in filtered:
            m = r.match(obj)

            if m is None:
                cls.log.error("invalid name on: {}".format(obj))
                invalid.append(obj)

            else:
                # if we have shader files and shader named group is in
                # regex, test this group against names in shader file
                if "shader" in r.groupindex and shaders:
                    try:
                        if not m.group('shader') in shaders:
                            cls.log.error(
                                "invalid materialID on: {0} ({1})".format(
                                    obj, m.group('shader')))

                            invalid.append(obj)
                    except IndexError:
                        # shader named group doesn't match
                        cls.log.error(
                            "shader group doesn't match: {}".format(obj))
                        invalid.append(obj)

        return invalid

    def process(self, instance):
        if not self.is_active(instance.data):
            return
        invalid = self.get_invalid(instance)

        if invalid:
            raise PublishValidationError(
                title="Model names are invalid",
                message="Model names are invalid.",
                description=self.get_description()
            )

    @classmethod
    def get_description(cls):
        return inspect.cleandoc(f"""
            ### Model content is invalid

            Must match required naming convention:

            - `AssetPart_IDmaterial_GEO`
        """)
