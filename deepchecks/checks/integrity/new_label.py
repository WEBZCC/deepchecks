"""The data_sample_leakage_report check module."""
from typing import Dict

from deepchecks import Dataset
from deepchecks.base.check import CheckResult, TrainTestBaseCheck, ConditionResult
from deepchecks.string_utils import format_percent

import pandas as pd

pd.options.mode.chained_assignment = None

__all__ = ['NewLabelTrainTest']


class NewLabelTrainTest(TrainTestBaseCheck):
    """Find new labels in test."""

    def run(self, train_dataset: Dataset, test_dataset: Dataset, model=None) -> CheckResult:
        """Run check.

        Args:
            train_dataset (Dataset): The training dataset object.
            test_dataset (Dataset): The test dataset object.
            model: any = None - not used in the check
        Returns:
            CheckResult: value is a dictionary that shows label column with new labels
            displays a dataframe that label columns with new labels
        Raises:
            DeepchecksValueError: If the datasets are not a Dataset instance or do not contain label column
        """
        return self._new_label_train_test(train_dataset=train_dataset,
                                          test_dataset=test_dataset)

    def _new_label_train_test(self, train_dataset: Dataset, test_dataset: Dataset):
        test_dataset = Dataset.validate_dataset_or_dataframe(test_dataset)
        train_dataset = Dataset.validate_dataset_or_dataframe(train_dataset)
        test_dataset.validate_label(self.__class__.__name__)
        train_dataset.validate_label(self.__class__.__name__)
        test_dataset.validate_shared_label(train_dataset, self.__class__.__name__)

        label_column = train_dataset.validate_shared_label(test_dataset, self.__class__.__name__)

        n_test_samples = test_dataset.n_samples()

        train_label = train_dataset.data[label_column]
        test_label = test_dataset.data[label_column]

        unique_training_values = set(train_label.unique())
        unique_test_values = set(test_label.unique())

        new_labels = unique_test_values.difference(unique_training_values)

        if new_labels:
            n_new_label = len(test_label[test_label.isin(new_labels)])

            dataframe = pd.DataFrame(data=[[label_column, format_percent(n_new_label / n_test_samples),
                                            sorted(new_labels)]],
                                     columns=['Label column', 'Percent new labels in sample', 'New labels'])
            dataframe = dataframe.set_index(['Label column'])

            display = dataframe

            result = {
                'column_name': label_column,
                'n_samples': n_test_samples,
                'n_new_labels_samples': n_new_label,
                'new_labels': sorted(new_labels)
            }
        else:
            display = None
            result = {}

        return CheckResult(result, check=self.run, display=display)

    def add_condition_new_labels_not_greater_than(self, max_new: int = 0):
        """Add condition - require label column not to have greater than given number of different new labels.

        Args:
            max_new (int): Number of different new labels value types which is the maximum allowed.
        """
        def condition(result: Dict) -> ConditionResult:
            if result:
                column_name = result['column_name']
                num_new_labels = len(result['new_labels'])
                if num_new_labels > max_new:
                    return ConditionResult(False,
                                           f'Found more than {max_new} new labels in label column: '
                                           f'{column_name}')
            return ConditionResult(True)

        return self.add_condition(f'Number of new label values is not greater than {max_new}',
                                  condition)

    def add_condition_new_label_ratio_not_greater_than(self, max_ratio: float = 0):
        """Add condition - require label column not to have greater than given number of ratio new label samples.

        Args:
            max_ratio (int): Ratio of new label samples to total samples which is the maximum allowed.
        """
        def new_category_count_condition(result: Dict) -> ConditionResult:
            if result:
                column_name = result['column_name']
                new_label_ratio = result['n_new_labels_samples']/result['n_samples']
                if new_label_ratio > max_ratio:
                    return ConditionResult(False,
                                           f'Found more than {format_percent(max_ratio)} new labeled data in'
                                           f' label column: {column_name}')
            return ConditionResult(True)

        return self.add_condition(
            f'Ratio of samples with new label is not greater than {format_percent(max_ratio)}',
            new_category_count_condition)