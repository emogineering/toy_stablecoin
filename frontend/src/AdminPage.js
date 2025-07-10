import React, { useEffect, useState } from 'react';

function AdminPage() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [approveMsg, setApproveMsg] = useState('');
  const [stats, setStats] = useState(null);
  const [transfers, setTransfers] = useState([]);
  const [burnAmount, setBurnAmount] = useState('');
  const [burnMemo, setBurnMemo] = useState('');
  const [burnMsg, setBurnMsg] = useState('');
  const [burns, setBurns] = useState([]);
  const [balanceMsg, setBalanceMsg] = useState('');

  const fetchStats = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/dashboard-stats');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      setStats(null);
    }
  };

  const fetchRequests = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/admin/mint-requests');
      const data = await res.json();
      setRequests(data);
    } catch (err) {
      setError('목록 불러오기 실패');
    }
    setLoading(false);
  };

  const fetchTransfers = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/upbit-transfers');
      const data = await res.json();
      setTransfers(data);
    } catch (err) {
      setTransfers([]);
    }
  };

  const fetchBurns = async () => {
    try {
      const res = await fetch('http://localhost:8000/admin/burn-requests');
      const data = await res.json();
      setBurns(data);
    } catch (err) {
      setBurns([]);
    }
  };

  useEffect(() => {
    fetchStats();
    fetchRequests();
    fetchTransfers();
    fetchBurns();
  }, []);

  const handleApprove = async (id) => {
    setApproveMsg('');
    try {
      const res = await fetch(`http://localhost:8000/admin/approve/${id}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '승인 실패');
      setApproveMsg(data.message);
      fetchRequests();
    } catch (err) {
      setApproveMsg(err.message);
    }
  };

  const handleManualBurn = async (e) => {
    e.preventDefault();
    setBurnMsg('');
    try {
      const res = await fetch('http://localhost:8000/admin/manual-burn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ amount: parseFloat(burnAmount), memo: burnMemo })
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '소각 신청 실패');
      setBurnMsg('소각 신청 완료!');
      setBurnAmount('');
      setBurnMemo('');
      fetchTransfers();
    } catch (err) {
      setBurnMsg(err.message);
    }
  };

  const handleApproveBurn = async (id) => {
    try {
      const res = await fetch(`http://localhost:8000/admin/approve-burn/${id}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '승인 실패');
      fetchBurns();
      fetchStats();
    } catch (err) {
      alert(err.message);
    }
  };
  const handleRejectBurn = async (id) => {
    try {
      const res = await fetch(`http://localhost:8000/admin/reject-burn/${id}`, { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '거절 실패');
      fetchBurns();
      fetchStats();
    } catch (err) {
      alert(err.message);
    }
  };

  const handleCheckBalanceChange = async () => {
    setBalanceMsg('');
    try {
      const res = await fetch('http://localhost:8000/admin/check-balance-change', { method: 'POST' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || '잔액 변화 감지 실패');
      setBalanceMsg(data.message);
      fetchRequests();
      fetchBurns();
      fetchStats();
    } catch (err) {
      setBalanceMsg(err.message);
    }
  };

  return (
    <div style={{ maxWidth: 700, margin: '40px auto', padding: 20, border: '1px solid #ccc', borderRadius: 8 }}>
      <h2>민팅 신청 목록 (관리자)</h2>
      {stats && (
        <div style={{ marginBottom: 20, padding: 10, background: '#f8f8f8', borderRadius: 6 }}>
          <b>계좌 USDT 잔액:</b> {stats.usdt_balance !== undefined ? Number(stats.usdt_balance).toFixed(6) : '-'} USDT<br/>
          <b>총 민팅된 USDG:</b> {stats.total_usdg_minted} USDG<br/>
          <b>총 소각된 USDG:</b> {stats.total_usdg_burned} USDG<br/>
          <b>현재 유통중인 USDG:</b> {stats.circulating_usdg !== undefined ? Number(stats.circulating_usdg).toFixed(6) : '-'} USDG
        </div>
      )}
      <h2>입출금 내역 (업비트)</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
        <thead>
          <tr>
            <th>구분</th><th>금액</th><th>통화</th><th>상태</th><th>트랜잭션ID</th><th>일시</th>
          </tr>
        </thead>
        <tbody>
          {transfers.map(tx => (
            <tr key={tx.id}>
              <td>{tx.type === 'deposit' ? '입금' : '출금'}</td>
              <td>{Number(tx.amount).toFixed(6)}</td>
              <td>{tx.currency}</td>
              <td>{tx.status}</td>
              <td style={{ fontSize: '0.9em' }}>{tx.tx_id}</td>
              <td>{tx.created_at ? new Date(new Date(tx.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <h2>소각 신청 목록</h2>
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 30 }}>
        <thead>
          <tr>
            <th>ID</th><th>금액</th><th>트랜잭션ID/메모</th><th>상태</th><th>신청일시</th><th>Action</th>
          </tr>
        </thead>
        <tbody>
          {burns.map(burn => (
            <tr key={burn.id}>
              <td>{burn.id}</td>
              <td>{Number(burn.amount).toFixed(6)}</td>
              <td>{burn.tx_id}</td>
              <td>{burn.status}</td>
              <td>{burn.created_at ? new Date(new Date(burn.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : '-'}</td>
              <td>
                {burn.status === 'pending' ? (
                  <>
                    <button onClick={() => handleApproveBurn(burn.id)}>승인</button>
                    <button onClick={() => handleRejectBurn(burn.id)} style={{ marginLeft: 8 }}>거절</button>
                  </>
                ) : burn.status === 'approved' ? '승인됨' : '거절됨'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{ margin: '30px 0', padding: 10, background: '#f3f3f3', borderRadius: 6 }}>
        <h3>임의 소각 신청</h3>
        <form onSubmit={handleManualBurn} style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
          <input type="number" min="0.000001" step="0.000001" placeholder="소각할 USDT 양" value={burnAmount} onChange={e => setBurnAmount(e.target.value)} required style={{ width: 120 }} />
          <input type="text" placeholder="메모(선택)" value={burnMemo} onChange={e => setBurnMemo(e.target.value)} style={{ width: 200 }} />
          <button type="submit">소각 신청</button>
        </form>
        {burnMsg && <div style={{ marginTop: 8, color: burnMsg.includes('완료') ? 'green' : 'red' }}>{burnMsg}</div>}
      </div>
      <div style={{ margin: '30px 0', padding: 10, background: '#f3f3f3', borderRadius: 6 }}>
        <h3>잔액 변화 감지</h3>
        <button onClick={handleCheckBalanceChange}>잔액 변화 확인</button>
        {balanceMsg && <div style={{ marginTop: 8, color: balanceMsg.includes('감지') ? 'green' : 'blue' }}>{balanceMsg}</div>}
      </div>
      {loading ? <div>불러오는 중...</div> : error ? <div style={{ color: 'red' }}>{error}</div> : (
        <table style={{ width: '100%', borderCollapse: 'collapse' }}>
          <thead>
            <tr>
              <th>ID</th><th>Address</th><th>Amount</th><th>Status</th><th>신청일시</th><th>Action</th>
            </tr>
          </thead>
          <tbody>
            {requests.map(req => (
              <tr key={req.id}>
                <td>{req.id}</td>
                <td>{req.eth_address}</td>
                <td>{req.amount}</td>
                <td>{req.status}</td>
                <td>{req.created_at ? new Date(new Date(req.created_at).getTime() + 9 * 60 * 60 * 1000).toLocaleString('ko-KR', { timeZone: 'Asia/Seoul' }) : '-'}</td>
                <td>
                  {req.status === 'pending' ? (
                    <button onClick={() => handleApprove(req.id)}>승인</button>
                  ) : '완료'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {approveMsg && <div style={{ marginTop: 20, color: approveMsg.includes('실패') ? 'red' : 'green' }}>{approveMsg}</div>}
      <button style={{ marginTop: 20 }} onClick={fetchRequests}>새로고침</button>
    </div>
  );
}

export default AdminPage; 