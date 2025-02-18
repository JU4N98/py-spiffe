import threading

import grpc
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509 import Certificate

from pyspiffe.proto.spiffe import workload_pb2
from pyspiffe.spiffe_id.spiffe_id import SpiffeId
from pyspiffe.spiffe_id.spiffe_id import TrustDomain
from pyspiffe.workloadapi.exceptions import FetchX509SvidError, FetchX509BundleError
from test.utils.utils import read_file_bytes
from test.workloadapi.test_default_workload_api_client import WORKLOAD_API_CLIENT
from test.utils.utils import (
    ResponseHolder,
    handle_success,
    handle_error,
    assert_error,
    FakeCall,
)

TEST_CERTS_PATH = 'test/svid/x509svid/certs/{}'
TEST_BUNDLE_PATH = 'test/bundle/x509bundle/certs/{}'
CHAIN1 = read_file_bytes(TEST_CERTS_PATH.format('1-chain.der'))
KEY1 = read_file_bytes(TEST_CERTS_PATH.format('1-key.der'))
CHAIN2 = read_file_bytes(TEST_CERTS_PATH.format('4-cert.der'))
KEY2 = read_file_bytes(TEST_CERTS_PATH.format('4-key.der'))
BUNDLE = read_file_bytes(TEST_BUNDLE_PATH.format('cert.der'))
FEDERATED_BUNDLE = read_file_bytes(TEST_BUNDLE_PATH.format('federated_bundle.der'))
CORRUPTED = read_file_bytes(TEST_CERTS_PATH.format('corrupted'))


def test_fetch_x509_svid_success(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                        ),
                    ]
                )
            ]
        )
    )

    svid = WORKLOAD_API_CLIENT.fetch_x509_svid()

    assert svid.spiffe_id() == SpiffeId.parse('spiffe://example.org/service')
    assert len(svid.cert_chain()) == 2
    assert isinstance(svid.leaf(), Certificate)
    assert isinstance(svid.private_key(), ec.EllipticCurvePrivateKey)


def test_fetch_x509_svid_empty_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter([workload_pb2.X509SVIDResponse(svids=[])])
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svid()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: X.509 SVID response is empty.'
    )


def test_fetch_x509_svid_invalid_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter([])
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svid()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: X.509 SVID response is invalid.'
    )


def test_fetch_x509_svid_raise_grpc_error_call(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        side_effect=FakeCall()
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svid()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: Error details from Workload API.'
    )


def test_fetch_x509_svid_raise_exception(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        side_effect=Exception('mocked error')
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svid()

    assert str(exception.value) == 'Error fetching X.509 SVID: mocked error.'


def test_fetch_x509_svid_corrupted_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CORRUPTED,
                            x509_svid_key=KEY1,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                        ),
                    ]
                )
            ]
        )
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svid()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: Unable to parse DER X.509 certificate.'
    )


def test_fetch_x509_svids_success(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                        ),
                    ]
                )
            ]
        )
    )

    svids = WORKLOAD_API_CLIENT.fetch_x509_svids()

    assert len(svids) == 2

    svid1 = svids[0]
    assert svid1.spiffe_id() == SpiffeId.parse('spiffe://example.org/service')
    assert len(svid1.cert_chain()) == 2
    assert isinstance(svid1.leaf(), Certificate)
    assert isinstance(svid1.private_key(), ec.EllipticCurvePrivateKey)

    svid2 = svids[1]
    assert svid2.spiffe_id() == SpiffeId.parse('spiffe://example.org/service2')
    assert len(svid2.cert_chain()) == 1
    assert isinstance(svid2.leaf(), Certificate)
    assert isinstance(svid2.private_key(), ec.EllipticCurvePrivateKey)


def test_fetch_x509_svids_empty_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter([workload_pb2.X509SVIDResponse(svids=[])])
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svids()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: X.509 SVID response is empty.'
    )


def test_fetch_x509_svids_invalid_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter([])
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svids()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: X.509 SVID response is invalid.'
    )


def test_fetch_x509_svids_raise_grpc_error_call(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        side_effect=FakeCall()
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svids()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: Error details from Workload API.'
    )


def test_fetch_x509_svids_raise_exception(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        side_effect=Exception('mocked error')
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svids()

    assert str(exception.value) == 'Error fetching X.509 SVID: mocked error.'


def test_fetch_x509_svids_corrupted_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CORRUPTED,
                            x509_svid_key=KEY2,
                        ),
                    ]
                )
            ]
        )
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_svids()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: Unable to parse DER X.509 certificate.'
    )


def test_fetch_x509_context_success(mocker):
    federated_bundles = {'domain.test': FEDERATED_BUNDLE}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                            bundle=BUNDLE,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                            bundle=BUNDLE,
                        ),
                    ],
                    federated_bundles=federated_bundles,
                )
            ]
        )
    )

    x509_context = WORKLOAD_API_CLIENT.fetch_x509_context()

    svids = x509_context.x509_svids()
    bundle_set = x509_context.x509_bundle_set()

    assert len(svids) == 2

    svid1 = x509_context.default_svid()
    assert svid1.spiffe_id() == SpiffeId.parse('spiffe://example.org/service')
    assert len(svid1.cert_chain()) == 2
    assert isinstance(svid1.leaf(), Certificate)
    assert isinstance(svid1.private_key(), ec.EllipticCurvePrivateKey)

    svid2 = x509_context.x509_svids()[1]
    assert svid2.spiffe_id() == SpiffeId.parse('spiffe://example.org/service2')
    assert len(svid2.cert_chain()) == 1
    assert isinstance(svid2.leaf(), Certificate)
    assert isinstance(svid2.private_key(), ec.EllipticCurvePrivateKey)

    bundle = bundle_set.get_x509_bundle_for_trust_domain(
        TrustDomain.parse('example.org')
    )
    assert bundle
    assert len(bundle.x509_authorities()) == 1

    federated_bundle = bundle_set.get_x509_bundle_for_trust_domain(
        TrustDomain.parse('domain.test')
    )
    assert federated_bundle
    assert len(federated_bundle.x509_authorities()) == 1


def test_fetch_x509_context_empty_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter([workload_pb2.X509SVIDResponse(svids=[])])
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: X.509 SVID response is empty.'
    )


def test_fetch_x509_context_invalid_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter([])
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: X.509 SVID response is invalid.'
    )


def test_fetch_x509_context_raise_grpc_error(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        side_effect=FakeCall()
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert (
        str(exception.value)
        == 'Error fetching X.509 SVID: Error details from Workload API.'
    )


def test_fetch_x509_context_raise_exception(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        side_effect=Exception('mocked error')
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert str(exception.value) == 'Error fetching X.509 SVID: mocked error.'


def test_fetch_x509_context_corrupted_svid(mocker):
    federated_bundles = {'domain.test': FEDERATED_BUNDLE}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=CORRUPTED,
                            bundle=BUNDLE,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                            bundle=BUNDLE,
                        ),
                    ],
                    federated_bundles=federated_bundles,
                )
            ]
        )
    )

    with (pytest.raises(FetchX509SvidError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert 'Error fetching X.509 SVID: Error parsing private key' in str(
        exception.value
    )


def test_fetch_x509_context_corrupted_bundle(mocker):
    federated_bundles = {'domain.test': FEDERATED_BUNDLE}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                            bundle=CORRUPTED,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                            bundle=CORRUPTED,
                        ),
                    ],
                    federated_bundles=federated_bundles,
                )
            ]
        )
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: Error parsing X.509 bundle: Unable to parse DER X.509 certificate.'
    )


def test_fetch_x509_context_corrupted_federated_bundle(mocker):
    federated_bundles = {'domain.test': CORRUPTED}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                            bundle=BUNDLE,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                            bundle=BUNDLE,
                        ),
                    ],
                    federated_bundles=federated_bundles,
                )
            ]
        )
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_context()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: Error parsing X.509 bundle: Unable to parse DER X.509 certificate.'
    )


def test_fetch_x509_bundles_success(mocker):
    bundles = {'example.org': BUNDLE, 'domain.test': FEDERATED_BUNDLE}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509BundlesResponse(
                    bundles=bundles,
                )
            ]
        )
    )

    bundle_set = WORKLOAD_API_CLIENT.fetch_x509_bundles()

    bundle = bundle_set.get_x509_bundle_for_trust_domain(
        TrustDomain.parse('example.org')
    )
    assert bundle
    assert len(bundle.x509_authorities()) == 1

    federated_bundle = bundle_set.get_x509_bundle_for_trust_domain(
        TrustDomain.parse('domain.test')
    )
    assert federated_bundle
    assert len(federated_bundle.x509_authorities()) == 1


def test_fetch_x509_bundles_empty_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        return_value=iter([workload_pb2.X509BundlesResponse(bundles=[])])
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_bundles()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: X.509 Bundles response is empty.'
    )


def test_fetch_x509_bundles_invalid_response(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        return_value=iter([])
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_bundles()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: X.509 Bundles response is invalid.'
    )


def test_fetch_x509_bundles_raise_grpc_error(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        side_effect=FakeCall()
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_bundles()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: Error details from Workload API.'
    )


def test_fetch_x509_bundles_raise_exception(mocker):
    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        side_effect=Exception('mocked error')
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_bundles()

    assert str(exception.value) == 'Error fetching X.509 Bundles: mocked error.'


def test_fetch_x509_bundles_corrupted_bundle(mocker):
    bundles = {'example.org': CORRUPTED, 'domain.test': FEDERATED_BUNDLE}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509BundlesResponse(
                    bundles=bundles,
                )
            ]
        )
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_bundles()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: Error parsing X.509 bundle: Unable to parse DER X.509 certificate.'
    )


def test_fetch_x509_bundles_corrupted_federated_bundle(mocker):
    bundles = {'example.org': BUNDLE, 'domain.test': CORRUPTED}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509Bundles = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509BundlesResponse(
                    bundles=bundles,
                )
            ]
        )
    )

    with (pytest.raises(FetchX509BundleError)) as exception:
        WORKLOAD_API_CLIENT.fetch_x509_bundles()

    assert (
        str(exception.value)
        == 'Error fetching X.509 Bundles: Error parsing X.509 bundle: Unable to parse DER X.509 certificate.'
    )


def test_watch_x509_context_success(mocker):
    federated_bundles = {'domain.test': FEDERATED_BUNDLE}

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=iter(
            [
                workload_pb2.X509SVIDResponse(
                    svids=[
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service',
                            x509_svid=CHAIN1,
                            x509_svid_key=KEY1,
                            bundle=BUNDLE,
                        ),
                        workload_pb2.X509SVID(
                            spiffe_id='spiffe://example.org/service2',
                            x509_svid=CHAIN2,
                            x509_svid_key=KEY2,
                            bundle=BUNDLE,
                        ),
                    ],
                    federated_bundles=federated_bundles,
                )
            ]
        )
    )

    done = threading.Event()
    response_holder = ResponseHolder()

    WORKLOAD_API_CLIENT.watch_x509_context(
        lambda r: handle_success(r, response_holder, done),
        lambda e: handle_error(e, response_holder, done),
        retry_connect=True,
    )

    done.wait(5)  # add timeout to prevent test from hanging

    assert not response_holder.error
    x509_context = response_holder.success
    svid1 = x509_context.default_svid()
    assert svid1.spiffe_id() == SpiffeId.parse('spiffe://example.org/service')
    assert len(svid1.cert_chain()) == 2
    assert isinstance(svid1.leaf(), Certificate)
    assert isinstance(svid1.private_key(), ec.EllipticCurvePrivateKey)

    svid2 = x509_context.x509_svids()[1]
    assert svid2.spiffe_id() == SpiffeId.parse('spiffe://example.org/service2')
    assert len(svid2.cert_chain()) == 1
    assert isinstance(svid2.leaf(), Certificate)
    assert isinstance(svid2.private_key(), ec.EllipticCurvePrivateKey)

    bundle_set = x509_context.x509_bundle_set()
    bundle = bundle_set.get_x509_bundle_for_trust_domain(
        TrustDomain.parse('example.org')
    )
    assert bundle
    assert len(bundle.x509_authorities()) == 1


def test_watch_x509_context_raise_retryable_grpc_error_and_then_ok_response(mocker):
    mock_error_iter = mocker.MagicMock()
    mock_error_iter.__iter__.side_effect = (
        yield_grpc_error_and_then_correct_x509_svid_response()
    )

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=mock_error_iter
    )

    expected_error = FetchX509SvidError('StatusCode.DEADLINE_EXCEEDED')
    done = threading.Event()

    response_holder = ResponseHolder()

    WORKLOAD_API_CLIENT.watch_x509_context(
        lambda r: handle_success(r, response_holder, done),
        lambda e: assert_error(e, expected_error),
        True,
    )

    done.wait(5)  # add timeout to prevent test from hanging

    x509_context = response_holder.success
    svid1 = x509_context.default_svid()
    assert svid1.spiffe_id() == SpiffeId.parse('spiffe://example.org/service')
    assert len(svid1.cert_chain()) == 2
    assert isinstance(svid1.leaf(), Certificate)
    assert isinstance(svid1.private_key(), ec.EllipticCurvePrivateKey)

    svid2 = x509_context.x509_svids()[1]
    assert svid2.spiffe_id() == SpiffeId.parse('spiffe://example.org/service2')
    assert len(svid2.cert_chain()) == 1
    assert isinstance(svid2.leaf(), Certificate)
    assert isinstance(svid2.private_key(), ec.EllipticCurvePrivateKey)

    bundle_set = x509_context.x509_bundle_set()
    bundle = bundle_set.get_x509_bundle_for_trust_domain(
        TrustDomain.parse('example.org')
    )
    assert bundle
    assert len(bundle.x509_authorities()) == 1


def test_watch_x509_context_raise_unretryable_grpc_error(mocker):
    grpc_error = grpc.RpcError()
    grpc_error.code = lambda: grpc.StatusCode.INVALID_ARGUMENT

    mock_error_iter = mocker.MagicMock()
    mock_error_iter.__iter__.side_effect = grpc_error

    WORKLOAD_API_CLIENT._spiffe_workload_api_stub.FetchX509SVID = mocker.Mock(
        return_value=mock_error_iter
    )

    done = threading.Event()
    expected_error = FetchX509SvidError('StatusCode.INVALID_ARGUMENT')

    response_holder = ResponseHolder()

    WORKLOAD_API_CLIENT.watch_x509_context(
        lambda r: handle_success(r, response_holder, done),
        lambda e: handle_error(e, response_holder, done),
        True,
    )

    done.wait(5)  # add timeout to prevent test from hanging

    assert not response_holder.success
    assert str(response_holder.error) == str(expected_error)


def yield_grpc_error_and_then_correct_x509_svid_response():
    grpc_error = grpc.RpcError()
    grpc_error.code = lambda: grpc.StatusCode.DEADLINE_EXCEEDED
    yield grpc_error

    federated_bundles = {'domain.test': FEDERATED_BUNDLE}
    response = iter(
        [
            workload_pb2.X509SVIDResponse(
                svids=[
                    workload_pb2.X509SVID(
                        spiffe_id='spiffe://example.org/service',
                        x509_svid=CHAIN1,
                        x509_svid_key=KEY1,
                        bundle=BUNDLE,
                    ),
                    workload_pb2.X509SVID(
                        spiffe_id='spiffe://example.org/service2',
                        x509_svid=CHAIN2,
                        x509_svid_key=KEY2,
                        bundle=BUNDLE,
                    ),
                ],
                federated_bundles=federated_bundles,
            )
        ]
    )
    yield response
