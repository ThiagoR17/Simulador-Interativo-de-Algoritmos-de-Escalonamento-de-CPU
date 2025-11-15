from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
from scheduler import Process, fcfs_scheduler_optimized, multi_level_queue_scheduler, sjf_preemptive_scheduler, rr_scheduler
import collections

app = Flask(__name__)
app.config['SECRET_KEY'] = 'secret!'
socketio = SocketIO(app)

SCHEDULER_MAP = {
    'fcfs': fcfs_scheduler_optimized,
    'sjf_preemptive': sjf_preemptive_scheduler,
    'round_robin': rr_scheduler,
    'multi_level': multi_level_queue_scheduler
}

@app.route('/')
def index():
    return render_template('index.html')

def run_simulation_for_user(sid, algorithm_name, processes_data, quantum_str):
    try:
        processes = [Process(p['pid'], p['arrival'], p['burst'], p.get('priority', 0)) for p in processes_data]
        
        scheduler_func = SCHEDULER_MAP.get(algorithm_name)
        if not scheduler_func:
            socketio.emit('simulation_error', {'error': f'Algoritmo desconhecido: {algorithm_name}'}, to=sid)
            return

        args = [processes]
        if algorithm_name == 'round_robin':
            args.append(int(quantum_str))
        
        scheduler_generator = scheduler_func(*args)

        if scheduler_generator:
            for state in scheduler_generator:
                if 'final_stats' in state:
                    stats = state['final_stats']
                    if not stats:
                        socketio.emit('simulation_end', {'stats': [], 'avg_wait': 0, 'avg_turnaround': 0}, to=sid)
                        return

                    avg_wait = sum(p['waiting_time'] for p in stats) / len(stats)
                    avg_turnaround = sum(p['turnaround_time'] for p in stats) / len(stats)
                    
                    socketio.emit('simulation_end', {'stats': stats, 'avg_wait': avg_wait, 'avg_turnaround': avg_turnaround}, to=sid)
                else:
                    socketio.emit('simulation_update', state, to=sid)
                    socketio.sleep(0.7)

    except Exception as e:
        print(f"Erro na simulação para {sid}: {e}")
        socketio.emit('simulation_error', {'error': str(e)}, to=sid)

@socketio.on('start_simulation')
def handle_start_simulation(data):
    user_sid = request.sid
    
    processes = data.get('processes', [])
    algorithm = data.get('algorithm', 'fcfs')
    quantum = data.get('quantum', '0')
    
    socketio.start_background_task(
        target=run_simulation_for_user,
        sid=user_sid,
        algorithm_name=algorithm,
        processes_data=processes,
        quantum_str=quantum
    )

@socketio.on('connect')
def handle_connect():
    print(f'Cliente conectado: {request.sid}')

@socketio.on('disconnect')
def handle_disconnect():
    print(f'Cliente desconhecido: {request.sid}')

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5000)