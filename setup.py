# Copyright (c) 2016 ATT
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import setuptools
from setuptools import find_packages

setuptools.setup(name="ord", version="2016.3.0",
                 packages=find_packages(),
                 include_package_data=True,
                 setup_requires=['pbr'],
                 pbr=True)
