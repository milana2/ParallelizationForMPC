from dataclasses import dataclass
import json
from tests.benchmark import BenchmarkOutput
from tests.statistics import CircuitStatistics, TimingStatistics, CommunicationStatistics, TimingDatapoint

@dataclass
class StatsForInputConfig:
    label: str
    gmw_p0: BenchmarkOutput
    gmw_p1: BenchmarkOutput
    gmw_vec_p0: BenchmarkOutput
    gmw_vec_p1: BenchmarkOutput
    bmr_p0: BenchmarkOutput
    bmr_p1: BenchmarkOutput
    bmr_vec_p0: BenchmarkOutput
    bmr_vec_p1: BenchmarkOutput

    @classmethod
    def from_dictionary(cls, params):
        label = params['label']
        gmw_p0 = params['gmw_p0']
        gmw_p1 = params['gmw_p1']
        gmw_vec_p0 = params['gmw_vec_p0']
        gmw_vec_p1 = params['gmw_vec_p1']
        bmr_p0 = params['bmr_p0']
        bmr_p1 = params['bmr_p1']
        bmr_vec_p0 = params['bmr_vec_p0']
        bmr_vec_p1 = params['bmr_vec_p1']

        return cls(
            label=label,
            gmw_p0=gmw_p0,
            gmw_p1=gmw_p1,
            gmw_vec_p0=gmw_vec_p0,
            gmw_vec_p1=gmw_vec_p1,
            bmr_p0=bmr_p0,
            bmr_p1=bmr_p1,
            bmr_vec_p0=bmr_vec_p0,
            bmr_vec_p1=bmr_vec_p1
            )

    def to_dictionary(self):
        return {
            'label': self.label,
            'gmw_p0': self.gmw_p0,
            'gmw_p1': self.gmw_p1,
            'gmw_vec_p0': self.gmw_vec_p0,
            'gmw_vec_p1': self.gmw_vec_p1,
            'bmr_p0': self.bmr_p0,
            'bmr_p1': self.bmr_p1,
            'bmr_vec_p0': self.bmr_vec_p0,
            'bmr_vec_p1': self.bmr_vec_p1,
        }


@dataclass
class StatsForTask:
    label: str
    input_configs: list[StatsForInputConfig]

    @classmethod
    def from_dictionary(cls, params):
        label = params['label']
        input_configs = params['input_configs']
        return cls(
            label=label,
            input_configs=input_configs
            )

    def to_dictionary(self):
        return {'label': self.label,
                'input_configs': self.input_configs
                }


def json_serialize(obj):
    return json.dumps(obj, default=_to_json)

def json_deserialize(json_str):
    return json.loads(json_str, object_hook=_from_json)

def _to_json(python_object):
    """
    serializes data objects used in the benchmark script
    :param python_object: object to serialize
    :return: json serialization `python_object`
    """

    if isinstance(python_object, TimingDatapoint):
        return  {'__class__': 'TimingDatapoint',
                 '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CommunicationStatistics):
        return {'__class__': 'CommunicationStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, TimingStatistics):
        return {'__class__': 'TimingStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, CircuitStatistics):
        return {'__class__': 'CircuitStatistics',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, BenchmarkOutput):
        return {'__class__': 'BenchmarkOutput',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, StatsForTask):
        return {'__class__': 'StatsForTask',
                '__value__': python_object.to_dictionary()}
    elif isinstance(python_object, StatsForInputConfig):
        return {'__class__': 'StatsForInputConfig',
                '__value__': python_object.to_dictionary()}

    raise TypeError(repr(python_object) + ' is not JSON serializable')


def _from_json(json_object):
    """
    deserializes data objects used in the benchmark script
    :param json: json serialization of an object
    :return: deserialized python object
    """
    if '__class__' in json_object:
        if json_object['__class__'] == 'TimingDatapoint':
            return TimingDatapoint.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'CommunicationStatistics':
            return CommunicationStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'TimingStatistics':
            return TimingStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'CircuitStatistics':
            return CircuitStatistics.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'BenchmarkOutput':
            return BenchmarkOutput.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'StatsForTask':
            return StatsForTask.from_dictionary(json_object['__value__'])
        elif json_object['__class__'] == 'StatsForInputConfig':
            return StatsForInputConfig.from_dictionary(json_object['__value__'])

    return json_object
